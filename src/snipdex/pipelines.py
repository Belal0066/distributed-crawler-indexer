# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import boto3
import json
import time
from datetime import datetime
import sys
import os

# Add the project root to the path to import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, INDEXER_QUEUE_NAME
)
from src.common.s3_utils import store_raw_content
from src.common.monitor import crawler_monitor


class SnipdexPipeline:
    def process_item(self, item, spider):
        return item


class SQSPipeline:
    def __init__(self):
        # Initialize SQS client
        self.sqs = boto3.client('sqs',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Get queue URLs
        try:
            response = self.sqs.get_queue_url(QueueName=INDEXER_QUEUE_NAME)
            self.indexer_queue_url = response['QueueUrl']
            print(f"Connected to indexer queue: {INDEXER_QUEUE_NAME}")
        except Exception as e:
            print(f"Error connecting to indexer queue: {e}")
            self.indexer_queue_url = None
        
        # Start monitoring
        self.monitor = crawler_monitor
        self.monitor.start()
    
    def process_item(self, item, spider):
        # Get item data
        adapter = ItemAdapter(item)
        url = adapter.get('url')
        
        # Skip if no URL
        if not url:
            print("Missing URL. Skipping.")
            return item
        
        try:
            # Store raw content in S3
            html_content = adapter.get('html', '')
            if html_content:
                store_result = store_raw_content(url, html_content)
                print(f"Stored raw content: {store_result.get('status')}")
            
            # Prepare data for indexing
            document_id = f"doc-{url.replace('://', '-').replace('/', '-')}"
            content = adapter.get('text', '')
            
            # Prepare metadata
            meta_data = {
                'url': url,
                'title': adapter.get('title', 'Untitled'),
                'description': adapter.get('description', ''),
                'keywords': adapter.get('keywords', []),
                'language': adapter.get('language', 'unknown'),
                'content_type': adapter.get('content_type', 'unknown'),
                'links': adapter.get('links', []),
                'status_code': adapter.get('status_code', 0),
                'crawl_time': adapter.get('timestamp', datetime.now().isoformat())
            }
            
            # Create message for indexer
            indexer_message = {
                'document_id': document_id,
                'content': content,
                'meta_data': meta_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send message to indexer queue
            if self.indexer_queue_url:
                response = self.sqs.send_message(
                    QueueUrl=self.indexer_queue_url,
                    MessageBody=json.dumps(indexer_message)
                )
                print(f"Sent to indexer queue: {document_id}")
                
                # Update metrics
                self.monitor.update_metric('pages_crawled', 1)
            else:
                print("Indexer queue URL not available. Skipping indexing.")
            
            return item
        except Exception as e:
            print(f"Error in SQS pipeline: {e}")
            self.monitor.update_metric('errors', 1)
            return item
    
    def close_spider(self, spider):
        self.monitor.stop()
