import boto3
import json
from datetime import datetime
from .aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME, S3_RAW_CONTENT_PATH, S3_INDEX_PATH, S3_METADATA_PATH,
    init_s3_bucket
)

# Initialize S3 client
s3 = boto3.client('s3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Initialize S3 bucket
init_s3_bucket()

def store_raw_content(url, content, content_type="text/html"):
    """
    Store raw content (e.g., HTML) in S3
    """
    # Create a safe file name from the URL
    safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_')
    key = f"{S3_RAW_CONTENT_PATH}{safe_name}.html"
    
    try:
        # Store the content in S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        
        return {
            'status': 'success',
            'bucket': S3_BUCKET_NAME,
            'key': key,
            'url': url,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'url': url
        }

def get_raw_content(url):
    """
    Retrieve raw content from S3
    """
    # Create a safe file name from the URL
    safe_name = url.replace('https://', '').replace('http://', '').replace('/', '_')
    key = f"{S3_RAW_CONTENT_PATH}{safe_name}.html"
    
    try:
        # Get the content from S3
        response = s3.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=key
        )
        
        # Extract the content
        content = response['Body'].read().decode('utf-8')
        
        return {
            'status': 'success',
            'content': content,
            'url': url,
            'key': key,
            'metadata': response.get('Metadata', {})
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'url': url
        }

def store_index_data(document_id, index_data):
    """
    Store indexed data in S3
    """
    # Create a safe file name
    safe_name = document_id.replace('https://', '').replace('http://', '').replace('/', '_')
    key = f"{S3_INDEX_PATH}{safe_name}.json"
    
    try:
        # Convert index data to JSON
        json_data = json.dumps(index_data)
        
        # Store the content in S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=json_data,
            ContentType='application/json'
        )
        
        return {
            'status': 'success',
            'bucket': S3_BUCKET_NAME,
            'key': key,
            'document_id': document_id,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'document_id': document_id
        }

def get_index_data(document_id):
    """
    Retrieve indexed data from S3
    """
    # Create a safe file name
    safe_name = document_id.replace('https://', '').replace('http://', '').replace('/', '_')
    key = f"{S3_INDEX_PATH}{safe_name}.json"
    
    try:
        # Get the content from S3
        response = s3.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=key
        )
        
        # Extract and parse the JSON content
        content = response['Body'].read().decode('utf-8')
        index_data = json.loads(content)
        
        return {
            'status': 'success',
            'index_data': index_data,
            'document_id': document_id,
            'key': key
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'document_id': document_id
        }

def list_raw_content():
    """
    List all raw content files in S3
    """
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=S3_RAW_CONTENT_PATH
        )
        
        if 'Contents' in response:
            return {
                'status': 'success',
                'files': [item['Key'] for item in response['Contents']]
            }
        else:
            return {
                'status': 'success',
                'files': []
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def list_index_data():
    """
    List all index data files in S3
    """
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=S3_INDEX_PATH
        )
        
        if 'Contents' in response:
            return {
                'status': 'success',
                'files': [item['Key'] for item in response['Contents']]
            }
        else:
            return {
                'status': 'success',
                'files': []
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def store_metadata(key, metadata):
    """
    Store system metadata in S3
    """
    metadata_key = f"{S3_METADATA_PATH}{key}.json"
    
    try:
        # Convert metadata to JSON
        json_data = json.dumps(metadata)
        
        # Store the metadata in S3
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=metadata_key,
            Body=json_data,
            ContentType='application/json'
        )
        
        return {
            'status': 'success',
            'bucket': S3_BUCKET_NAME,
            'key': metadata_key
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'key': key
        }

def get_metadata(key):
    """
    Retrieve system metadata from S3
    """
    metadata_key = f"{S3_METADATA_PATH}{key}.json"
    
    try:
        # Get the metadata from S3
        response = s3.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=metadata_key
        )
        
        # Extract and parse the JSON content
        content = response['Body'].read().decode('utf-8')
        metadata = json.loads(content)
        
        return {
            'status': 'success',
            'metadata': metadata,
            'key': key
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'key': key
        } 