import os
import sys
from pathlib import Path

try:
    import boto3
except ImportError:
    print("Error: boto3 is not installed. Please run: pip install boto3")
    sys.exit(1)

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from config.aws_config import (
        AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    )
except ImportError as e:
    print(f"Error importing aws_config: {e}")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def create_sqs_queues(sqs):
    """Create SQS queues for the system."""
    queues = {
        'crawler_queue': {
            'QueueName': 'crawler-task-queue',
            'Attributes': {
                'VisibilityTimeout': '3600',  # 1 hour
                'MessageRetentionPeriod': '86400',  # 1 day
                'DelaySeconds': '0'
            }
        },
        'indexer_queue': {
            'QueueName': 'indexer-task-queue',
            'Attributes': {
                'VisibilityTimeout': '3600',
                'MessageRetentionPeriod': '86400',
                'DelaySeconds': '0'
            }
        },
        'monitoring_queue': {
            'QueueName': 'monitoring-queue',
            'Attributes': {
                'VisibilityTimeout': '300',  # 5 minutes
                'MessageRetentionPeriod': '86400',
                'DelaySeconds': '0'
            }
        }
    }
    
    queue_urls = {}
    for queue_name, queue_config in queues.items():
        response = sqs.create_queue(
            QueueName=queue_config['QueueName'],
            Attributes=queue_config['Attributes']
        )
        queue_urls[queue_name] = response['QueueUrl']
        print(f"Created queue: {queue_config['QueueName']}")
    
    return queue_urls

def create_s3_bucket(s3):
    """Create S3 bucket for storing crawled data."""
    bucket_name = f"crawler-indexer-data-{AWS_ACCESS_KEY_ID[-8:].lower()}"
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
        )
        print(f"Created S3 bucket: {bucket_name}")
        return bucket_name
    except s3.exceptions.BucketAlreadyExists:
        print(f"Bucket {bucket_name} already exists")
        return bucket_name

def main():
    # Initialize AWS clients
    sqs = boto3.client('sqs',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    s3 = boto3.client('s3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Create SQS queues
    queue_urls = create_sqs_queues(sqs)
    
    # Create S3 bucket
    bucket_name = create_s3_bucket(s3)
    
    # Print environment variables to set
    print("\nSet these environment variables in your system:")
    print(f"export AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID}")
    print(f"export AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY}")
    print(f"export CRAWLER_QUEUE_URL={queue_urls['crawler_queue']}")
    print(f"export INDEXER_QUEUE_URL={queue_urls['indexer_queue']}")
    print(f"export MONITORING_QUEUE_URL={queue_urls['monitoring_queue']}")
    print(f"export S3_BUCKET_NAME={bucket_name}")

if __name__ == '__main__':
    main() 