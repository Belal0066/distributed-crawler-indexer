import boto3

sqs = boto3.client('sqs', region_name='eu-north-1')
queue_url = 'https://sqs.eu-north-1.amazonaws.com/425079547341/crawl-task-queue'

seed_urls = [
    "https://example.com",
    "https://wikipedia.org"
]

for url in seed_urls:
    sqs.send_message(QueueUrl=queue_url, MessageBody=url)
