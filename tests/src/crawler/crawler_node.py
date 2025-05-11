import boto3, requests
from bs4 import BeautifulSoup

sqs = boto3.client('sqs', region_name='eu-north-1')
s3 = boto3.client('s3')
queue_url = 'https://sqs.eu-north-1.amazonaws.com/425079547341/crawl-task-queue'
bucket_name = 'my-web-crawl-data'

while True:
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
    for msg in messages.get('Messages', []):
        url = msg['Body']
        html = requests.get(url).text
        s3.put_object(Bucket=bucket_name, Key=f"raw/{url.replace('https://','').replace('/','_')}.html", Body=html)
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg['ReceiptHandle'])