from celery import Celery
import os

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    'master_node',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
app.conf.update(
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

@app.task(name='crawlerI.crawl_url_task', queue='crawl_tasks')
def crawl_url_task(url, allowed_domains, job_id, depth):
    """
    Task to crawl a URL. The actual crawling logic is handled by the crawler in snipdex.
    This task just coordinates the crawling process.
    """
    try:
        return {
            'url': url,
            'status': 'success',
            'job_id': job_id,
            'depth': depth,
            'allowed_domains': allowed_domains
        }
    except Exception as e:
        return {
            'url': url,
            'status': 'error',
            'error': str(e)
        }

@app.task(name='indexer_node.index_content_task', queue='ingest_tasks')
def index_content_task(data):
    """
    Task to index content. The actual indexing logic is handled by the indexer.
    This task just coordinates the indexing process.
    """
    try:
        return {
            'status': 'indexed',
            'url': data.get('url'),
            'summary': data.get('content', '')[:200] if data.get('content') else ''
        }
    except Exception as e:
        return {
            'status': 'error',
            'url': data.get('url'),
            'error': str(e)
        } 