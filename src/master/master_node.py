from typing import List, Optional, Dict
import os
from celery import Celery
from elasticsearch import Elasticsearch

class MasterNode:
    def __init__(self):
        # Initialize Celery
        self.celery_app = Celery(
            'master_node',
            broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
        )
        
        # Initialize Elasticsearch
        self.es = Elasticsearch([os.getenv("ES_HOST", "http://localhost:9200")])
        
        # Configure Celery
        self.celery_app.conf.update(
            task_routes={
                'crawlerI.crawl_url_task': {'queue': 'crawl_tasks'},
                'indexer_node.index_content_task': {'queue': 'ingest_tasks'},
            },
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
        )

    def submit_crawl_job(self, urls: List[str], allowed_domains: Optional[List[str]] = None, 
                        job_id: Optional[str] = None, depth: int = 1) -> Dict:
        """Submit a new crawl job and trigger indexing."""
        task_ids = []
        for url in urls:
            # Submit crawl task
            crawl_task = self.celery_app.send_task(
                'crawlerI.crawl_url_task',
                args=[url, ','.join(allowed_domains or []), job_id, depth],
                queue='crawl_tasks'
            )
            task_ids.append(crawl_task.id)
            
            # Chain with indexing task
            index_task = self.celery_app.send_task(
                'indexer_node.index_content_task',
                args=[{'url': url}],
                queue='ingest_tasks'
            )
        
        job_id = job_id or (task_ids[0] if task_ids else "none")
        return {
            'job_id': job_id,
            'status': "submitted",
            'crawl_status': "pending",
            'index_status': "pending"
        }

    def get_job_status(self, job_id: str) -> Dict:
        """Get the status of both crawl and index jobs."""
        async_result = self.celery_app.AsyncResult(job_id)
        status = async_result.status
        result = async_result.result if async_result.ready() else None
        
        crawl_status = status
        index_status = "pending"
        
        if result and result.get('url'):
            try:
                index_result = self.es.get(index="my_index", id=result['url'])
                index_status = "completed" if index_result else "pending"
            except:
                index_status = "pending"
        
        return {
            'job_id': job_id,
            'status': status,
            'result': result,
            'crawl_status': crawl_status,
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
            
            response = self.es.search(index="my_index", body=search_query)
            
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
            
            return results
            
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")

    def check_health(self) -> Dict:
        """Check the health of all components."""
        try:
            redis_status = self.celery_app.connection().connect()
            es_status = self.es.ping()
            
            return {
                "status": "ok",
                "redis": "connected" if redis_status else "disconnected",
                "elasticsearch": "connected" if es_status else "disconnected"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            } 