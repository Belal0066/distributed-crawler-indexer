from elasticsearch import Elasticsearch
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
import json
import time
import boto3
import os
import threading
import socket
import uuid
import random
from datetime import datetime

# Import common modules
from common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    INDEXER_QUEUE_NAME, MONITORING_QUEUE_NAME
)
from common.s3_utils import get_raw_content, store_index_data, get_index_data
from common.monitor import indexer_monitor

# Generate a unique node ID
NODE_ID = f"indexer-{socket.gethostname()}-{uuid.uuid4()}"

# Ensure NLTK resources are downloaded
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Elasticsearch setup
es = Elasticsearch([os.getenv("ES_HOST", "http://localhost:9200")])

# Create the index if it doesn't exist
def initialize_elasticsearch():
    try:
        if not es.indices.exists(index="snipdex"):
            es.indices.create(
                index="snipdex",
                body={
                    "mappings": {
                        "properties": {
                            "content": {"type": "text"},
                            "meta_data": {
                                "properties": {
                                    "url": {"type": "keyword"},
                                    "title": {"type": "text"},
                                    "description": {"type": "text"},
                                    "keywords": {"type": "text"},
                                    "language": {"type": "keyword"}
                                }
                            },
                            "indexed_at": {"type": "date"},
                            "indexed_by": {"type": "keyword"}
                        }
                    }
                }
            )
            print("Created Elasticsearch index: snipdex")
        else:
            print("Elasticsearch index 'snipdex' already exists")
    except Exception as e:
        print(f"Error initializing Elasticsearch: {e}")

# Run initialization at module load time
initialize_elasticsearch()

# Initialize SQS client
sqs = boto3.client('sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Get indexer queue URL
try:
    response = sqs.get_queue_url(QueueName=INDEXER_QUEUE_NAME)
    INDEXER_QUEUE_URL = response['QueueUrl']
    print(f"Connected to indexer queue: {INDEXER_QUEUE_NAME}")
except Exception as e:
    print(f"Error connecting to indexer queue: {e}")
    INDEXER_QUEUE_URL = None

# Get monitoring queue URL
try:
    response = sqs.get_queue_url(QueueName=MONITORING_QUEUE_NAME)
    MONITORING_QUEUE_URL = response['QueueUrl']
    print(f"Connected to monitoring queue: {MONITORING_QUEUE_NAME}")
except Exception as e:
    print(f"Error connecting to monitoring queue: {e}")
    MONITORING_QUEUE_URL = None

# Track indexed documents for replication
indexed_documents = {}  # document_id -> {timestamp, replicated}

# Configure replication settings
REPLICATION_FACTOR = 2  # Number of replicas to maintain
REPLICATION_PROBABILITY = 0.3  # Probability of being selected as a replication node

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
        'node_type': 'indexer',
        'task_id': task_id,
        'status': status,
        'timestamp': datetime.now().isoformat(),
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

# Preprocessing function
def preprocess_content(content):
    """Preprocess content for indexing"""
    # Tokenize the content (split into words)
    tokens = word_tokenize(content.lower())
    # Remove stopwords
    stop_words = set(stopwords.words("english"))
    filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
    # Apply stemming
    stemmer = PorterStemmer()
    stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
    # Join tokens back into a single string
    return " ".join(stemmed_tokens)

def index_content(data):
    """
    Preprocess and index content into Elasticsearch.
    Expects data to be a dict with 'document_id', 'content' and 'meta_data'.
    """
    try:
        document_id = data.get("document_id")
        content = data.get("content", "")
        meta_data = data.get("meta_data", {})
        task_type = data.get("task_type", "index")
        
        # Skip if no document ID
        if not document_id:
            print("Missing document ID. Skipping.")
            return {"status": "error", "error": "Missing document ID"}
        
        # Send task started status
        send_task_status(document_id, 'started', {
            'document_id': document_id,
            'task_type': task_type
        })
        
        # Check if this is a replication task
        is_replication = task_type == "replicate"
        
        # If replication task, first check if we already have this document
        if is_replication and document_id in indexed_documents:
            print(f"Document {document_id} already indexed on this node. Skipping replication.")
            send_task_status(document_id, 'completed', {
                'document_id': document_id,
                'task_type': task_type,
                'already_indexed': True
            })
            return {"status": "already_indexed", "id": document_id}
        
        # Check if content exists
        if not content and "url" in meta_data:
            # Try to get raw content from S3
            raw_content_response = get_raw_content(meta_data["url"])
            if raw_content_response["status"] == "success":
                content = raw_content_response["content"]
        
        # For replication, try to get preprocessed content from S3
        if is_replication and not content:
            index_data_response = get_index_data(document_id)
            if index_data_response["status"] == "success":
                preprocessed = index_data_response["data"].get("content")
                meta_data = index_data_response["data"].get("meta_data", meta_data)
            else:
                print(f"No content for replication of document {document_id}. Skipping.")
                send_task_status(document_id, 'failed', {
                    'document_id': document_id,
                    'task_type': task_type,
                    'error': "No content for replication"
                })
                return {"status": "error", "error": "No content for replication"}
        else:
            # Skip if no content
            if not content:
                print(f"No content for document {document_id}. Skipping.")
                send_task_status(document_id, 'failed', {
                    'document_id': document_id,
                    'task_type': task_type,
                    'error': "No content to index"
                })
                return {"status": "error", "error": "No content to index"}
            
            # Preprocess content
            preprocessed = preprocess_content(content)
        
        # Prepare document for indexing
        doc = {
            "content": preprocessed,
            "meta_data": meta_data,
            "indexed_at": time.time(),
            "indexed_by": NODE_ID
        }
        
        # Index document
        resp = es.index(index="snipdex", id=document_id, document=doc, refresh=True)
        
        # Store index data in S3
        store_index_data(document_id, doc)
        
        # Track indexed document
        indexed_documents[document_id] = {
            'timestamp': time.time(),
            'replicated': is_replication
        }
        
        # Send task completed status
        send_task_status(document_id, 'completed', {
            'document_id': document_id,
            'task_type': task_type
        })
        
        # Update metrics
        indexer_monitor.update_metric('documents_indexed', 1)
        if is_replication:
            indexer_monitor.update_metric('documents_replicated', 1)
        
        return {"status": "indexed", "id": resp["_id"]}
    except Exception as e:
        # Update error metrics
        indexer_monitor.update_metric('errors', 1)
        print(f"Error indexing content: {e}")
        
        # Send task failed status
        send_task_status(document_id, 'failed', {
            'document_id': document_id,
            'task_type': task_type,
            'error': str(e)
        })
        
        return {"status": "error", "error": str(e)}

def should_replicate():
    """Determine if this node should handle replication tasks"""
    return random.random() < REPLICATION_PROBABILITY

def poll_queue():
    """Poll SQS queue for messages and process them"""
    if not INDEXER_QUEUE_URL:
        print("Indexer queue URL not available. Skipping poll.")
        return
    
    try:
        # Receive messages from queue
        response = sqs.receive_message(
            QueueUrl=INDEXER_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20  # Long polling
        )
        
        messages = response.get('Messages', [])
        
        for message in messages:
            try:
                # Parse message body
                receipt_handle = message['ReceiptHandle']
                body = json.loads(message['Body'])
                
                # Check if this is a replication task
                task_type = body.get('task_type', 'index')
                if task_type == 'replicate' and not should_replicate():
                    # Skip replication task if this node is not selected
                    continue
                
                # Process message
                document_id = body.get('document_id')
                print(f"Processing message: {document_id} (type: {task_type})")
                result = index_content(body)
                
                # If successful, delete message from queue
                if result.get('status') in ['indexed', 'already_indexed']:
                    sqs.delete_message(
                        QueueUrl=INDEXER_QUEUE_URL,
                        ReceiptHandle=receipt_handle
                    )
                    print(f"Indexed document: {result.get('id')}")
                else:
                    print(f"Failed to index document: {result.get('error')}")
                    # Message will be returned to the queue after visibility timeout expires
            except Exception as e:
                print(f"Error processing message: {e}")
                indexer_monitor.update_metric('errors', 1)
    except Exception as e:
        print(f"Error polling queue: {e}")
        indexer_monitor.update_metric('errors', 1)

def run_indexer():
    """Main loop for the indexer node"""
    # Start monitoring
    indexer_monitor.start()
    
    # Set node ID in monitor
    indexer_monitor.node_id = NODE_ID
    
    print(f"Indexer node started with ID {NODE_ID}. Polling for messages...")
    
    try:
        while True:
            poll_queue()
            time.sleep(1)  # Small delay between polls
    except KeyboardInterrupt:
        print("Indexer node stopping...")
        indexer_monitor.stop()

# Main entrypoint
if __name__ == "__main__":
    # Run the indexer
    run_indexer()