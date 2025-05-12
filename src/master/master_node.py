from typing import List, Optional, Dict
import os
import boto3
import json
import time
from datetime import datetime
from elasticsearch import Elasticsearch
import logging
# Import common modules
from common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, INDEXER_QUEUE_NAME, MONITORING_QUEUE_NAME
)
from common.s3_utils import store_metadata, get_metadata
from common.monitor import master_monitor
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
        
        # Initialize Elasticsearch
        self.es = Elasticsearch([os.getenv("ES_HOST", "http://localhost:9200")])
        
        # Get queue URLs
        self.get_queue_urls()
        
        # Start monitoring
        self.monitor = master_monitor
        self.monitor.start()
    
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
        """Submit a new crawl job and trigger indexing."""
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
            response = self.sqs.send_message(
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

    def search_content(self, query: str) -> List[Dict]:
        """Search through indexed content using Elasticsearch."""
        if not query:
            return []
        
        try:
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["content", "meta_data.title^2", "meta_data.description"],
                        "type": "best_fields"
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {},
                        "meta_data.title": {},
                        "meta_data.description": {}
                    }
                }
            }
            # logger.debug(f"DEBUG: Sending query to Elasticsearch: {search_query}")
            response = self.es.search(index="snipdex", body=search_query)
            # logger.debug(f"DEBUG: Elasticsearch response: {response}")

            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                meta_data = source.get('meta_data', {})
                
                highlights = hit.get('highlight', {})
                content_highlight = ' '.join(highlights.get('content', [])) if highlights.get('content') else None
                title_highlight = ' '.join(highlights.get('meta_data.title', [])) if highlights.get('meta_data.title') else None
                
                results.append({
                    'url': hit['_id'],
                    'title': meta_data.get('title', 'No title'),
                    'summary': content_highlight or meta_data.get('description', '')[:200],
                    'score': hit['_score'],
                    'highlights': {
                        'content': content_highlight,
                        'title': title_highlight
                    }
                })
            
            # Update metrics
            
            self.monitor.update_metric('searches', 1)
            return results
            
        except Exception as e:
            self.monitor.update_metric('errors', 1)
            # logger.error(f"Search failed with error: {str(e)}")
            raise Exception(f"Search failed: {str(e)}")

    def check_health(self) -> Dict:
        """Check the health of all components."""
        try:
            # Check SQS queues
            try:
                self.sqs.get_queue_attributes(QueueUrl=self.crawl_queue_url, AttributeNames=['All'])
                crawl_queue_status = "connected"
            except:
                crawl_queue_status = "disconnected"
            
            try:
                self.sqs.get_queue_attributes(QueueUrl=self.indexer_queue_url, AttributeNames=['All'])
                indexer_queue_status = "connected"
            except:
                indexer_queue_status = "disconnected"
            
            # Check Elasticsearch
            es_status = self.es.ping()
            
            # Get node metrics
            node_metrics = self.monitor.metrics
            
            return {
                "status": "ok",
                "crawl_queue": crawl_queue_status,
                "indexer_queue": indexer_queue_status,
                "elasticsearch": "connected" if es_status else "disconnected",
                "metrics": node_metrics
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

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
