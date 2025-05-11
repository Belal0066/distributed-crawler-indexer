import scrapy
from datetime import datetime, timezone
from snipdex.items import SnipdexItem
from scrapy.loader import ItemLoader
from urllib.parse import urljoin
import boto3
import json
import time
import os
import subprocess
import sys

# Add the project root to the path to import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME
)
from src.common.monitor import crawler_monitor

# Initialize SQS client
sqs = boto3.client('sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Get crawler queue URL
try:
    response = sqs.get_queue_url(QueueName=CRAWL_QUEUE_NAME)
    CRAWLER_QUEUE_URL = response['QueueUrl']
    print(f"Connected to crawler queue: {CRAWL_QUEUE_NAME}")
except Exception as e:
    print(f"Error connecting to crawler queue: {e}")
    CRAWLER_QUEUE_URL = None

def start_crawler_for_url(url, allowed_domains=None, job_id=None, depth=1):
    """
    Start a Scrapy crawler for a given URL and parameters.
    """
    # Prepare arguments for Scrapy crawl
    allowed_domains_str = ','.join(allowed_domains.split(',')) if allowed_domains else ''
    cmd = [
        'scrapy', 'crawl', 'crawlerI',
        '-a', f'start_urls={url}',
        '-a', f'allowed_domains={allowed_domains_str}',
        '-a', f'job_id={job_id}',
        '-a', f'depth={depth}'
    ]
    
    # Run Scrapy as a subprocess
    try:
        print(f"Starting crawler for {url}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log the result
        print(f"Crawler finished for {url} with return code: {result.returncode}")
        if result.returncode != 0:
            print(f"Crawler error: {result.stderr}")
        
        # Update monitoring metrics
        crawler_monitor.update_metric('crawl_tasks_processed', 1)
        if result.returncode != 0:
            crawler_monitor.update_metric('errors', 1)
        
        return {
            'status': 'finished' if result.returncode == 0 else 'error',
            'url': url,
            'job_id': job_id,
            'returncode': result.returncode
        }
    except Exception as e:
        print(f"Error starting crawler: {e}")
        crawler_monitor.update_metric('errors', 1)
        return {
            'status': 'error',
            'url': url,
            'job_id': job_id,
            'error': str(e)
        }

def poll_queue():
    """
    Poll SQS queue for crawl tasks
    """
    if not CRAWLER_QUEUE_URL:
        print("Crawler queue URL not available. Skipping poll.")
        return
    
    try:
        # Receive messages from queue
        response = sqs.receive_message(
            QueueUrl=CRAWLER_QUEUE_URL,
            MaxNumberOfMessages=1,  # Process one at a time to avoid overloading
            WaitTimeSeconds=20  # Long polling
        )
        
        messages = response.get('Messages', [])
        
        for message in messages:
            try:
                # Parse message body
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                
                # Extract task parameters
                url = body.get('url')
                allowed_domains = body.get('allowed_domains', '')
                job_id = body.get('job_id')
                depth = int(body.get('depth', 1))
                
                # Skip if no URL
                if not url:
                    print("Missing URL in task. Skipping.")
                    continue
                
                # Start crawler
                result = start_crawler_for_url(url, allowed_domains, job_id, depth)
                
                # Delete message from queue if successful
                if result.get('status') == 'finished':
                    sqs.delete_message(
                        QueueUrl=CRAWLER_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                    print(f"Processed and removed task for URL: {url}")
                else:
                    print(f"Failed to process task for URL: {url}, error: {result.get('error')}")
                    # Message will be returned to the queue after visibility timeout expires
            except Exception as e:
                print(f"Error processing message: {e}")
                crawler_monitor.update_metric('errors', 1)
    except Exception as e:
        print(f"Error polling queue: {e}")
        crawler_monitor.update_metric('errors', 1)

def run_crawler_worker():
    """
    Main function to run the crawler worker
    """
    # Start monitoring
    crawler_monitor.start()
    
    print("Crawler worker started. Polling for messages...")
    
    try:
        while True:
            poll_queue()
            time.sleep(1)  # Small delay between polls
    except KeyboardInterrupt:
        print("Crawler worker stopping...")
        crawler_monitor.stop()

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

        # HTML content for storage
        loader.add_value("html", response.text)

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

# Main entrypoint to run the worker
if __name__ == "__main__":
    run_crawler_worker()
