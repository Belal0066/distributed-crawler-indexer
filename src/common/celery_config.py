from celery import Celery
import os
from .aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, INDEXER_QUEUE_NAME, MONITORING_QUEUE_NAME,
    init_sqs_queues
)

# Initialize SQS queues and get their URLs
queue_urls = init_sqs_queues()

# Broker URL for SQS
broker_url = f'sqs://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@'

# Create a default Celery app
app = Celery('distributed_crawler')

# Configure the broker connection
app.conf.broker_url = broker_url
app.conf.broker_transport_options = {
    'region': AWS_REGION,
    'visibility_timeout': 3600,  # 1 hour
    'polling_interval': 1,       # 1 second
    'queue_name_prefix': '',     # No prefix for queue names
}

# Use the same broker as the result backend for simplicity
# In production, you might want a more persistent result backend
app.conf.result_backend = 'rpc://'
app.conf.result_persistent = True

# Task settings
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Worker settings
app.conf.worker_prefetch_multiplier = 1  # Don't prefetch tasks
app.conf.task_acks_late = True          # Only acknowledge after task completion
app.conf.task_track_started = True      # Track when tasks are started

# Route tasks to the appropriate queues
app.conf.task_routes = {
    'crawlerI.crawl_url_task': {'queue': CRAWL_QUEUE_NAME},
    'indexer_node.index_content_task': {'queue': INDEXER_QUEUE_NAME},
    'monitor.heartbeat_task': {'queue': MONITORING_QUEUE_NAME}
}

# Define the tasks
@app.task(name='crawlerI.crawl_url_task', queue=CRAWL_QUEUE_NAME)
def crawl_url_task(url, allowed_domains=None, job_id=None, depth=1):
    """
    This is a placeholder - the actual implementation is in the crawler module.
    This is just for task registration in the Celery app.
    """
    pass

@app.task(name='indexer_node.index_content_task', queue=INDEXER_QUEUE_NAME)
def index_content_task(data):
    """
    This is a placeholder - the actual implementation is in the indexer module.
    This is just for task registration in the Celery app.
    """
    pass

@app.task(name='monitor.heartbeat_task', queue=MONITORING_QUEUE_NAME)
def heartbeat_task(node_id, status):
    """
    This is a placeholder - the actual implementation will be elsewhere.
    This is just for task registration in the Celery app.
    """
    pass 