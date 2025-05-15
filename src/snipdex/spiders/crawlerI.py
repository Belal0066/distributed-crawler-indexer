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
import socket
import uuid
from src.common.fault_tolerance import fault_manager
import requests

# Add the project root to the path to import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from src.common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, MONITORING_QUEUE_NAME
)
from src.common.monitor import crawler_monitor

# Generate a unique node ID
NODE_ID = f"crawler-{socket.gethostname()}-{uuid.uuid4()}"

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

# Get monitoring queue URL
try:
    response = sqs.get_queue_url(QueueName=MONITORING_QUEUE_NAME)
    MONITORING_QUEUE_URL = response['QueueUrl']
    print(f"Connected to monitoring queue: {MONITORING_QUEUE_NAME}")
except Exception as e:
    print(f"Error connecting to monitoring queue: {e}")
    MONITORING_QUEUE_URL = None

def send_task_status(task_id, status, details=None):
    """
    Send task status update to the monitoring queue
    """
    if not MONITORING_QUEUE_URL:
        print("Monitoring queue URL not available. Skipping task status update.")
        return
    
    # Create status message
    status_message = {
        'node_id': NODE_ID,
        'node_type': 'crawler',
        'task_id': task_id,
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'details': details or {}
    }
    
    # Send message to queue
    try:
        response = sqs.send_message(
            QueueUrl=MONITORING_QUEUE_URL,
            MessageBody=json.dumps(status_message)
        )
        return response
    except Exception as e:
        print(f"Error sending task status: {e}")

def start_crawler_for_url(url, allowed_domains=None, job_id=None, depth=1, task_id=None):
    """
    Start a Scrapy crawler for a given URL and parameters.
    """
    # Get the scrapy project directory (where scrapy.cfg is located)
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Get the src directory for Python path
    src_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # Generate task ID if not provided
    if not task_id:
        task_id = f"task-{int(time.time())}-{hash(url) % 10000}"
    
    # Send task started status
    send_task_status(task_id, 'started', {
        'url': url,
        'job_id': job_id,
        'depth': depth
    })
    
    # Register this task with the fault tolerance manager
    fault_manager.register_task(task_id, NODE_ID)
    
    # Prepare arguments for Scrapy crawl
    allowed_domains_str = ','.join(allowed_domains.split(',')) if allowed_domains else ''
    cmd = [
        'scrapy', 'crawl', 'crawlerI',
        '-a', f'start_urls={url}',
        '-a', f'allowed_domains={allowed_domains_str}',
        '-a', f'job_id={job_id}',
        '-a', f'depth={depth}',
        '-a', f'task_id={task_id}'
    ]
    
    # Run Scrapy as a subprocess
    try:
        print(f"Starting crawler for {url}")
        print(f"Running command: {' '.join(cmd)}")
        print(f"From directory: {project_root}")
        
        # Set up environment variables for Scrapy
        env_vars = dict(os.environ)
        env_vars['PYTHONPATH'] = src_dir
        
        # Run the command from the scrapy project root directory (where scrapy.cfg is)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            env=env_vars
        )
        
        # Log the result
        print(f"Crawler finished for {url} with return code: {result.returncode}")
        if result.returncode != 0:
            print(f"Crawler error output:")
            print(result.stderr)
            print(f"Crawler standard output:")
            print(result.stdout)
            
            # Send task failed status
            send_task_status(task_id, 'failed', {
                'url': url,
                'job_id': job_id,
                'error': result.stderr,
                'returncode': result.returncode
            })
        else:
            print(f"Crawler standard output:")
            print(result.stdout)
            
            # Send task completed status
            send_task_status(task_id, 'completed', {
                'url': url,
                'job_id': job_id
            })
        
        # Update monitoring metrics
        crawler_monitor.update_metric('crawl_tasks_processed', 1)
        if result.returncode != 0:
            crawler_monitor.update_metric('errors', 1)
        
        return {
            'status': 'finished' if result.returncode == 0 else 'error',
            'url': url,
            'job_id': job_id,
            'task_id': task_id,
            'returncode': result.returncode,
            'error': result.stderr if result.returncode != 0 else None,
            'output': result.stdout
        }
    except Exception as e:
        print(f"Error starting crawler: {e}")
        crawler_monitor.update_metric('errors', 1)
        
        # Send task failed status
        send_task_status(task_id, 'failed', {
            'url': url,
            'job_id': job_id,
            'error': str(e)
        })
        
        return {
            'status': 'error',
            'url': url,
            'job_id': job_id,
            'task_id': task_id,
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
                task_id = body.get('task_id')
                depth = int(body.get('depth', 1))
                
                # Skip if no URL
                if not url:
                    print("Missing URL in task. Skipping.")
                    continue
                
                # Start crawler
                result = start_crawler_for_url(url, allowed_domains, job_id, depth, task_id)
                
                # Delete message from queue if successful
                if result.get('status') == 'finished':
                    sqs.delete_message(
                        QueueUrl=CRAWLER_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                    print(f"Processed and removed task for URL: {url}")
                    
                    # Mark task as complete in fault tolerance manager
                    fault_manager.complete_task(task_id)
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"Failed to process task for URL: {url}")
                    print(f"Error details: {error_msg}")
                    if result.get('output'):
                        print(f"Crawler output: {result.get('output')}")
                    # Message will be returned to the queue after visibility timeout expires
            except Exception as e:
                print(f"Error processing message: {e}")
                crawler_monitor.update_metric('errors', 1)
    except Exception as e:
        print(f"Error polling queue: {e}")
        crawler_monitor.update_metric('errors', 1)

def run_crawler_worker(check_shutdown=None):
    """
    Main function to run the crawler worker

    Args:
        check_shutdown: A function that returns True if shutdown is requested
    """
    print("Starting crawler worker...")
    print(f"Worker ID: {NODE_ID}")
    
    # Start monitoring
    crawler_monitor.start()
    
    try:
        while True:
            # Check if shutdown requested
            if check_shutdown and check_shutdown():
                print("Shutdown requested, stopping crawler worker")
                break
                
            # Poll and process tasks
            poll_queue()
            
            # Brief pause between polls
            time.sleep(1)
    except KeyboardInterrupt:
        print("Crawler worker interrupted")
    except Exception as e:
        print(f"Crawler worker error: {e}")
        crawler_monitor.update_metric('errors', 1)
        raise  # Re-raise to be handled by the parent
    finally:
        print("Crawler worker stopping...")
        # We don't stop the monitor as it may still be sending heartbeats

class CrawleriSpider(scrapy.Spider):
    name = "crawlerI"
    allowed_domains = []
    start_urls = []

    def __init__(self, start_urls=None, allowed_domains=None, job_id=None, depth=None, task_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if start_urls:
            self.start_urls = start_urls.split(',') if isinstance(start_urls, str) else start_urls
        if allowed_domains:
            self.allowed_domains = allowed_domains.split(',') if isinstance(allowed_domains, str) else allowed_domains
        self.job_id = job_id
        self.depth = int(depth) if depth else 1
        self.task_id = task_id
        
        # Send task progress status
        if self.task_id:
            send_task_status(self.task_id, 'crawling', {
                'url': self.start_urls[0] if self.start_urls else None,
                'job_id': self.job_id
            })

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
        # Limit to 5 unique links per page
        unique_links = unique_links[:5]
        item["links"] = unique_links

        # If depth > 1, send extracted URLs to master for recursive crawling
        if self.depth and self.depth > 1 and unique_links:
            try:
                api_url = os.getenv("MASTER_API_URL", "http://localhost:8000/crawl/recursive")
                payload = {
                    "urls": unique_links,
                    "allowed_domains": self.allowed_domains,
                    "job_id": self.job_id,
                    "depth": self.depth
                }
                resp = requests.post(api_url, json=payload, timeout=30)
                if resp.ok:
                    self.logger.info(f"Submitted {len(unique_links)} URLs for recursive crawling to master.")
                else:
                    self.logger.error(f"Failed to submit recursive URLs: {resp.text}")
            except Exception as e:
                self.logger.error(f"Error submitting recursive URLs: {e}")

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
