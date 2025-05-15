from typing import List, Optional, Dict
import os
import boto3
import json
import time
from datetime import datetime
from elasticsearch import Elasticsearch
import logging
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
# Import common modules
from common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, INDEXER_QUEUE_NAME, MONITORING_QUEUE_NAME
)
from common.s3_utils import store_metadata, get_metadata, get_raw_content
from common.monitor import master_monitor
from common.fault_tolerance import fault_manager
# Configure logging at the top of the file
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class MasterNode:
    def __init__(self):
        # Initialize SQS client
        self.sqs = boto3.client('sqs',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Initialize Elasticsearch with longer timeout and retry configuration
        self.es = Elasticsearch(
            hosts=os.getenv("ES_HOST", "http://localhost:9200").split(),  # Split by spaces
            request_timeout=60,  # 60 second timeout
            retry_on_timeout=True,
            max_retries=3
        )
        
        # Get queue URLs
        self.get_queue_urls()
        
        # Start monitoring
        self.monitor = master_monitor
        self.monitor.start()
        
        # Start fault tolerance manager
        fault_manager.start()
    
    def get_queue_urls(self):
        """Get SQS queue URLs"""
        try:
            crawl_response = self.sqs.get_queue_url(QueueName=CRAWL_QUEUE_NAME)
            self.crawl_queue_url = crawl_response['QueueUrl']
            
            indexer_response = self.sqs.get_queue_url(QueueName=INDEXER_QUEUE_NAME)
            self.indexer_queue_url = indexer_response['QueueUrl']
            
            monitoring_response = self.sqs.get_queue_url(QueueName=MONITORING_QUEUE_NAME)
            self.monitoring_queue_url = monitoring_response['QueueUrl']
            
            print(f"Queue URLs initialized: {CRAWL_QUEUE_NAME}, {INDEXER_QUEUE_NAME}, {MONITORING_QUEUE_NAME}")
        except Exception as e:
            print(f"Error getting queue URLs: {e}")
            raise

    def submit_crawl_job(self, urls: List[str], allowed_domains: Optional[List[str]] = None, 
                        job_id: Optional[str] = None, depth: int = 1) -> Dict:
        """Submit a new crawl job and trigger indexing. Also supports recursive crawling by depth."""
        if not job_id:
            job_id = f"job-{int(time.time())}"
        # Create job metadata
        job_metadata = {
            'job_id': job_id,
            'urls': urls,
            'allowed_domains': allowed_domains or [],
            'depth': depth,
            'status': 'submitted',
            'submission_time': datetime.now().isoformat(),
            'task_ids': []
        }
        # Store job metadata in S3
        store_metadata(f"jobs/{job_id}", job_metadata)
        task_ids = []
        for url in urls:
            # Create task message
            task_id = f"task-{job_id}-{int(time.time())}-{len(task_ids)}"
            task_data = {
                'task_id': task_id,
                'job_id': job_id,
                'url': url,
                'allowed_domains': ','.join(allowed_domains or []),
                'depth': depth,
                'task_type': 'crawl',
                'timestamp': datetime.now().isoformat()
            }
            # Submit task to SQS
            self.sqs.send_message(
                QueueUrl=self.crawl_queue_url,
                MessageBody=json.dumps(task_data)
            )
            task_ids.append(task_id)
            self.monitor.update_metric('tasks_created', 1)
        # Update job metadata with task IDs
        job_metadata['task_ids'] = task_ids
        job_metadata['status'] = 'in_progress'
        store_metadata(f"jobs/{job_id}", job_metadata)
        return {
            'job_id': job_id,
            'status': "submitted",
            'crawl_status': "pending",
            'index_status': "pending",
            'task_count': len(task_ids)
        }

    def submit_recursive_crawl_tasks(self, urls: List[str], allowed_domains: Optional[List[str]], job_id: str, depth: int):
        """Submit new crawl tasks for extracted URLs if depth > 1."""
        if depth > 1:
            self.submit_crawl_job(urls, allowed_domains, job_id, depth-1)

    def get_job_status(self, job_id: str) -> Dict:
        """Get the status of both crawl and index jobs."""
        # Get job metadata from S3
        job_response = get_metadata(f"jobs/{job_id}")
        
        if job_response['status'] != 'success':
            return {
                'job_id': job_id,
                'status': 'unknown',
                'error': f"Job metadata not found: {job_response.get('error')}"
            }
        
        job_metadata = job_response['metadata']
        
        # Check Elasticsearch for indexed content
        task_ids = job_metadata.get('task_ids', [])
        indexed_count = 0
        
        for task_id in task_ids:
            try:
                index_result = self.es.get(index="snipdex", id=task_id)
                if index_result:
                    indexed_count += 1
            except:
                pass
        
        # Calculate status
        if indexed_count == len(task_ids):
            index_status = "completed"
        elif indexed_count > 0:
            index_status = "in_progress"
        else:
            index_status = "pending"
        
        return {
            'job_id': job_id,
            'status': job_metadata.get('status', 'unknown'),
            'submission_time': job_metadata.get('submission_time'),
            'urls': job_metadata.get('urls', []),
            'task_count': len(task_ids),
            'indexed_count': indexed_count,
            'crawl_status': job_metadata.get('status', 'unknown'),
            'index_status': index_status
        }
        
    def preprocess_query(self, query: str) -> str:
        # Tokenize the query (split into words)
        tokens = word_tokenize(query.lower())
        # Remove stopwords
        stop_words = set(stopwords.words("english"))
        filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
        # Apply stemming
        stemmer = PorterStemmer()
        stemmed_tokens = [stemmer.stem(word) for word in filtered_tokens]
        # Join tokens back into a single string
        return " ".join(stemmed_tokens)

    def search_content(self, query: str, search_type: str = "match", limit: int = 10, fetch_content: bool = False) -> List[Dict]:
        """Search through indexed content using Elasticsearch with different search types."""
        if not query:
            return []
        try:
            # Preprocess query for match/phrase
            if search_type in ("match", "phrase"):
                processed_query = self.preprocess_query(query)
            else:
                processed_query = query

            logger.debug(f"Processed query: {processed_query}")
            logger.debug(f"Search type: {search_type}")

            if search_type == "phrase":
                search_query = {
                    "query": {
                        "multi_match": {
                            "query": processed_query,
                            "fields": ["content", "meta_data.title^2", "meta_data.description"],
                            "type": "phrase"
                        }
                    },
                    "size": limit,
                    "highlight": {
                        "fields": {
                            "content": {},
                            "meta_data.title": {},
                            "meta_data.description": {}
                        }
                    }
                }
            elif search_type == "boolean":
                search_query = {
                    "query": {
                        "query_string": {
                            "query": processed_query,
                            "fields": ["content", "meta_data.title^2", "meta_data.description"]
                        }
                    },
                    "size": limit,
                    "highlight": {
                        "fields": {
                            "content": {},
                            "meta_data.title": {},
                            "meta_data.description": {}
                        }
                    }
                }
            else:  # Default to 'match' with fuzziness
                search_query = {
                    "query": {
                        "multi_match": {
                            "query": processed_query,
                            "fields": ["content", "meta_data.title^2", "meta_data.description"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    "size": limit,
                    "highlight": {
                        "fields": {
                            "content": {},
                            "meta_data.title": {},
                            "meta_data.description": {}
                        }
                    }
                }
            logger.debug(f"Elasticsearch query: {search_query}")
            
            # Set a timeout for Elasticsearch search
            response = self.es.search(index="snipdex", body=search_query, request_timeout=30)
            
            logger.debug(f"Elasticsearch response: {response}")
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                meta_data = source.get('meta_data', {})
                url = meta_data.get('url', hit['_id'])
                highlights = hit.get('highlight', {})
                content_highlight = ' '.join(highlights.get('content', [])) if highlights.get('content') else None
                title_highlight = ' '.join(highlights.get('meta_data.title', [])) if highlights.get('meta_data.title') else None

                # Fetch raw content from S3 only if explicitly requested
                raw_content = None
                if fetch_content:
                    try:
                        s3_result = get_raw_content(url)
                        if s3_result.get("status") == "success":
                            raw_content = s3_result.get("content")
                    except Exception as e:
                        logger.error(f"Failed to fetch raw content for {url}: {e}")

                results.append({
                    'url': url,
                    'title': meta_data.get('title', 'No title'),
                    'summary': content_highlight or meta_data.get('description', '')[:200],
                    'score': hit['_score'],
                    'raw_content': raw_content,
                    'highlights': {
                        'content': content_highlight,
                        'title': title_highlight
                    }
                })
            self.monitor.update_metric('searches', 1)
            return results
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            # Track the error
            self.monitor.update_metric('search_errors', 1)
            # Provide a clear message for API error handling
            error_msg = f"Search operation failed: {str(e)}"
            if "ConnectionTimeout" in str(e) or "timed out" in str(e).lower():
                error_msg = "Elasticsearch connection timed out. The search index may be temporarily unavailable."
            elif "ConnectionError" in str(e):
                error_msg = "Could not connect to Elasticsearch. The search service may be down."
            # Re-raise with a more informative message
            raise Exception(error_msg)

    def check_health(self) -> Dict:
        """Check the overall system health."""
        try:
            # Check SQS queues
            queues_ok = True
            try:
                # Check if we can connect to the queues (just get attributes)
                self.sqs.get_queue_attributes(
                    QueueUrl=self.crawl_queue_url,
                    AttributeNames=['ApproximateNumberOfMessages']
                )
                self.sqs.get_queue_attributes(
                    QueueUrl=self.indexer_queue_url,
                    AttributeNames=['ApproximateNumberOfMessages']
                )
            except Exception as e:
                queues_ok = False
                print(f"SQS queue check failed: {e}")
            
            # Check Elasticsearch
            es_ok = True
            try:
                es_status = self.es.cluster.health()
                es_status = es_status.get('status')  # 'green', 'yellow', or 'red'
            except Exception as e:
                es_ok = False
                es_status = f"Error: {str(e)}"
                print(f"Elasticsearch check failed: {e}")
            
            # Get fault tolerance status
            ft_status = fault_manager.get_status()
            
            # Format response
            return {
                "status": "healthy" if queues_ok else "degraded",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "sqs": {
                        "status": "online" if queues_ok else "offline"
                    },
                    # "elasticsearch": {
                    #     "status": es_status
                    # },
                    "fault_tolerance": ft_status
                }
            }
        except Exception as e:
            # Return error
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    def check_fault_tolerance(self) -> Dict:
        """Get detailed fault tolerance status."""
        return fault_manager.get_status()

# Main entrypoint
if __name__ == "__main__":
    master = MasterNode()
    print("Master Node started. Ready to process tasks.")
    
    # Keep the process running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Master Node stopping...")
        master.monitor.stop()
