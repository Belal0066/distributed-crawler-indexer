import os

# AWS Region
AWS_REGION = os.getenv('AWS_REGION', 'your-aws-region')  # e.g. 'eu-north-1'

# AWS Credentials - DO NOT hardcode these values in production!
# Use environment variables instead
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'your-access-key-id')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'your-secret-access-key')

# SQS Queue Names and URLs
CRAWL_QUEUE_NAME = 'crawler-task-queue'
INDEXER_QUEUE_NAME = 'indexer-task-queue'
MONITORING_QUEUE_NAME = 'monitoring-queue'

# SQS Queue URLs - set by environment or discovered at runtime
CRAWL_QUEUE_URL = os.getenv('CRAWL_QUEUE_URL', None)
INDEXER_QUEUE_URL = os.getenv('INDEXER_QUEUE_URL', None)
MONITORING_QUEUE_URL = os.getenv('MONITORING_QUEUE_URL', None)

# S3 Configuration
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'crawler-indexer-data')

# S3 Folder Paths
S3_RAW_CONTENT_PATH = 'raw/'
S3_INDEX_PATH = 'index/'
S3_METADATA_PATH = 'metadata/'

# Elasticsearch Configuration (unchanged)
ES_HOST = os.getenv('ES_HOST', 'http://localhost:9200')

# Function to initialize SQS queues and get their URLs
def init_sqs_queues():
    import boto3
    
    sqs = boto3.client('sqs',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Queue attributes
    queue_attributes = {
        CRAWL_QUEUE_NAME: {
            'VisibilityTimeout': '3600',  # 1 hour
            'MessageRetentionPeriod': '86400',  # 1 day
            'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
        },
        INDEXER_QUEUE_NAME: {
            'VisibilityTimeout': '3600',  # 1 hour
            'MessageRetentionPeriod': '86400',  # 1 day
            'ReceiveMessageWaitTimeSeconds': '5'  # Long polling
        },
        MONITORING_QUEUE_NAME: {
            'VisibilityTimeout': '300',  # 5 minutes
            'MessageRetentionPeriod': '86400',  # 1 day
            'ReceiveMessageWaitTimeSeconds': '5'  # Long polling
        }
    }
    
    # Create or get queue URLs
    queue_urls = {}
    for queue_name, attributes in queue_attributes.items():
        try:
            # Try to get existing queue
            response = sqs.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            print(f"Found existing queue: {queue_name}")
        except:
            # Create queue if it doesn't exist
            response = sqs.create_queue(
                QueueName=queue_name,
                Attributes=attributes
            )
            queue_url = response['QueueUrl']
            print(f"Created new queue: {queue_name}")
        
        queue_urls[queue_name] = queue_url
    
    # Return the queue URLs
    return queue_urls

# Function to initialize S3 bucket
def init_s3_bucket():
    import boto3
    
    s3 = boto3.client('s3',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Create bucket if it doesn't exist
    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"Found existing bucket: {S3_BUCKET_NAME}")
    except:
        try:
            # Note: for regions other than us-east-1, need to specify LocationConstraint
            create_bucket_config = {}
            if AWS_REGION != 'us-east-1':
                create_bucket_config = {
                    'LocationConstraint': AWS_REGION
                }
            
            response = s3.create_bucket(
                Bucket=S3_BUCKET_NAME,
                CreateBucketConfiguration=create_bucket_config
            )
            print(f"Created new bucket: {S3_BUCKET_NAME}")
        except Exception as e:
            print(f"Error creating bucket: {e}")
    
    return S3_BUCKET_NAME

# Initialize AWS resources on module import if running as main script
if __name__ == "__main__":
    queue_urls = init_sqs_queues()
    print(f"SQS Queues: {queue_urls}")
    
    bucket_name = init_s3_bucket()
    print(f"S3 Bucket: {bucket_name}") 