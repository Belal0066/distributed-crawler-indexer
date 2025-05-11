from celery import Celery
from .aws_config import AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# Celery Configuration
app = Celery('distributed_crawler')

# Broker settings
app.conf.broker_url = f'sqs://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@'
app.conf.broker_transport_options = {
    'region': AWS_REGION,
    'visibility_timeout': 3600,  # 1 hour
    'polling_interval': 1,  # 1 second
}

# Result backend settings
app.conf.result_backend = 'rpc://'
app.conf.result_persistent = True

# Task settings
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Worker settings
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
app.conf.task_track_started = True

# Queue routing
app.conf.task_routes = {
    'tasks.crawl_url': {'queue': 'crawler_queue'},
    'tasks.index_content': {'queue': 'indexer_queue'},
    'tasks.heartbeat': {'queue': 'monitoring_queue'}
} 