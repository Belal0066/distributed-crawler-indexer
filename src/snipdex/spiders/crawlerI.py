import scrapy
from datetime import datetime, timezone
from snipdex.items import SnipdexItem
from scrapy.loader import ItemLoader
from urllib.parse import urljoin
from celery import Celery
import os
import subprocess
import json

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    'crawlerI',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

@celery_app.task(name='crawlerI.crawl_url_task', queue='crawl_tasks')
def crawl_url_task(url, allowed_domains, job_id, depth):
    """
    Celery task to run the crawler for a given URL and parameters.
    Launches Scrapy programmatically and returns the parsed result.
    """
    # Prepare arguments for Scrapy crawl
    allowed_domains_str = ','.join(allowed_domains.split(',')) if allowed_domains else ''
    cmd = [
        'scrapy', 'crawl', 'crawlerI',
        f'-a', f'start_urls={url}',
        f'-a', f'allowed_domains={allowed_domains_str}',
        f'-a', f'job_id={job_id}',
        f'-a', f'depth={depth}'
    ]
    # Run Scrapy as a subprocess and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Optionally, parse output or store results
    # For now, just return the status and output
    return {
        'status': 'finished',
        'url': url,
        'job_id': job_id,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'returncode': result.returncode
    }

class CrawleriSpider(scrapy.Spider):
    name = "crawlerI"
    allowed_domains = []
    start_urls = []

    def __init__(self, start_urls=None, allowed_domains=None, job_id=None, depth=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_urls:
            self.start_urls = start_urls.split(",")
        if allowed_domains:
            self.allowed_domains = allowed_domains.split(",")
        self.job_id = job_id
        self.depth = int(depth) if depth else None

    def parse(self, response):
        loader = ItemLoader(item=SnipdexItem(), response=response)

        # HTTP status
        loader.add_value("status_code", response.status)

        # Basic metadata
        loader.add_value("url", response.url)
        loader.add_xpath("title", "//title/text()")

        # Description with fallback
        loader.add_xpath("description", "//meta[@name='description']/@content")
        if not loader.get_output_value("description"):
            loader.add_xpath("description", "//meta[@property='og:description']/@content")

        # Keywords with fallback
        loader.add_xpath("keywords", "//meta[@name='keywords']/@content")
        if not loader.get_output_value("keywords"):
            loader.add_xpath("keywords", "//meta[@property='article:tag']/@content")

        # Text extraction
        text_xpath = """
        //body//*[not(self::script) and not(self::style)]
                 [not(ancestor::script) and not(ancestor::style) 
                  and not(ancestor::nav) and not(ancestor::footer) 
                  and not(ancestor::header)]
                 /text()
        """
        loader.add_xpath("text", text_xpath)

        # Link extraction (raw)
        loader.add_css("links", "a::attr(href)")

        # Timestamp
        loader.add_value("timestamp", datetime.now(timezone.utc).isoformat())

        # Content-Type
        content_type = response.headers.get("Content-Type")
        loader.add_value("content_type", content_type.decode() if content_type else "unknown")

        # Language
        lang = response.xpath("//html/@lang").get()
        loader.add_value("language", lang if lang else "und")

        # Final item
        item = loader.load_item()

        # Normalize + deduplicate links
        base_url = response.url
        raw_links = item.get("links", [])
        normalized_links = [urljoin(base_url, href) for href in raw_links if href.strip()]
        seen = set()
        unique_links = []
        for link in normalized_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        item["links"] = unique_links

        # Apply fallback defaults
        for field, default in {
            "description": "N/A",
            "keywords": [],
            "title": "Untitled",
            "language": "und",
            "text": "",
            "links": [],
        }.items():
            item.setdefault(field, default)

        yield item
