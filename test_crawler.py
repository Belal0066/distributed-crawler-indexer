#!/usr/bin/env python3
"""
Test script to submit URLs to the crawler queue.
"""
import boto3
import json
import time
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import AWS configuration
from src.common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME
)

def send_test_urls():
    """Send test URLs to the crawler queue."""
    # Initialize SQS client
    sqs = boto3.client('sqs',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Get the crawler queue URL
    try:
        response = sqs.get_queue_url(QueueName=CRAWL_QUEUE_NAME)
        queue_url = response['QueueUrl']
    except Exception as e:
        print(f"Error getting queue URL: {e}")
        return
    
    # Test URLs to crawl
    test_urls = [
        "https://www.example.com",
        "https://www.python.org",
        "https://www.wikipedia.org"
    ]
    
    job_id = f"test-job-{int(time.time())}"
    
    # Send each URL to the queue
    for url in test_urls:
        # Create task message
        task_id = f"task-{job_id}-{int(time.time())}-{test_urls.index(url)}"
        task_data = {
            'task_id': task_id,
            'job_id': job_id,
            'url': url,
            'allowed_domains': '',
            'depth': 1,
            'task_type': 'crawl',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }
        
        # Send message to SQS
        try:
            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(task_data)
            )
            print(f"Sent URL to crawler queue: {url}")
            print(f"Message ID: {response.get('MessageId')}")
        except Exception as e:
            print(f"Error sending message: {e}")
    
    print(f"Submitted {len(test_urls)} URLs with job ID: {job_id}")
    print("Done! The crawler nodes should now process these URLs.")

if __name__ == "__main__":
    send_test_urls() 