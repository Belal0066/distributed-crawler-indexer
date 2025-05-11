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

# Import common modules
from common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    INDEXER_QUEUE_NAME
)
from common.s3_utils import get_raw_content, store_index_data
from common.monitor import indexer_monitor

# Ensure NLTK resources are downloaded
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Elasticsearch setup
es = Elasticsearch([os.getenv("ES_HOST", "http://localhost:9200")])

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
        
        # Skip if no document ID
        if not document_id:
            print("Missing document ID. Skipping.")
            return {"status": "error", "error": "Missing document ID"}
        
        # Check if content exists
        if not content and "url" in meta_data:
            # Try to get raw content from S3
            raw_content_response = get_raw_content(meta_data["url"])
            if raw_content_response["status"] == "success":
                content = raw_content_response["content"]
        
        # Skip if no content
        if not content:
            print(f"No content for document {document_id}. Skipping.")
            return {"status": "error", "error": "No content to index"}
        
        # Preprocess content
        preprocessed = preprocess_content(content)
        
        # Prepare document for indexing
        doc = {
            "content": preprocessed,
            "meta_data": meta_data,
            "indexed_at": time.time()
        }
        
        # Index document
        resp = es.index(index="my_index", id=document_id, document=doc, refresh=True)
        
        # Store index data in S3
        store_index_data(document_id, doc)
        
        # Update metrics
        indexer_monitor.update_metric('documents_indexed', 1)
        
        return {"status": "indexed", "id": resp["_id"]}
    except Exception as e:
        # Update error metrics
        indexer_monitor.update_metric('errors', 1)
        print(f"Error indexing content: {e}")
        return {"status": "error", "error": str(e)}

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
                
                # Process message
                print(f"Processing message: {body.get('document_id')}")
                result = index_content(body)
                
                # If successful, delete message from queue
                if result.get('status') == 'indexed':
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
    
    print("Indexer node started. Polling for messages...")
    
    try:
        while True:
            poll_queue()
            time.sleep(1)  # Small delay between polls
    except KeyboardInterrupt:
        print("Indexer node stopping...")
        indexer_monitor.stop()

# Main entrypoint
if __name__ == "__main__":
    # Ensure Elasticsearch index exists
    if not es.indices.exists(index="my_index"):
        es.indices.create(
            index="my_index",
            body={
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "meta_data": {
                            "properties": {
                                "title": {"type": "text"},
                                "description": {"type": "text"},
                                "url": {"type": "keyword"}
                            }
                        },
                        "indexed_at": {"type": "date"}
                    }
                }
            }
        )
        print("Created Elasticsearch index: my_index")
    
    # Run the indexer
    run_indexer()