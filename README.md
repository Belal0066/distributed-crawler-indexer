# Distributed Crawler-Indexer with AWS SQS

A distributed web crawling and indexing system using AWS SQS as a message broker. This system consists of a Master Node, Crawler Nodes, and Indexer Nodes, with AWS S3 for storage.

## Architecture

- **Master Node**: Manages crawl jobs and provides API endpoints
- **Crawler Nodes**: Crawl websites and extract content
- **Indexer Nodes**: Process and index content for search
- **AWS SQS**: Message queues for communication
- **AWS S3**: Storage for raw content and indexed data
- **Elasticsearch**: Search engine for indexed content

## Requirements

- Python 3.8+
- AWS Account with access to SQS, S3, and EC2
- AWS Access Key and Secret Key with appropriate permissions
- Git (for deployment)

## Local Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/distributed-crawler-indexer.git
   cd distributed-crawler-indexer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables for AWS:
   ```
   export AWS_ACCESS_KEY_ID='your-access-key'
   export AWS_SECRET_ACCESS_KEY='your-secret-key'
   export AWS_REGION='eu-north-1'  # Or your preferred region
   ```

4. Initialize AWS resources:
   ```
   python -c "from src.common.aws_config import init_sqs_queues, init_s3_bucket; init_sqs_queues(); init_s3_bucket()"
   ```

5. Run the master node:
   ```
   python src/master_node.py
   ```

6. In separate terminals, run crawler and indexer workers:
   ```
   python src/crawler_worker.py
   python src/indexer_worker.py
   ```

## AWS Deployment

The system can be automatically deployed to AWS EC2 instances:

1. Set environment variables for AWS:
   ```
   export AWS_ACCESS_KEY_ID='your-access-key'
   export AWS_SECRET_ACCESS_KEY='your-secret-key'
   export AWS_REGION='eu-north-1'  # Or your preferred region
   ```

2. Run the deployment script:
   ```
   python src/deploy_aws.py --repo-url 'your-github-repo-url' --master-count 1 --crawler-count 2 --indexer-count 1
   ```

3. After deployment, you can access the API at:
   ```
   http://<master-node-ip>:8000
   ```

## API Usage

The API provides the following endpoints:

- `GET /`: Welcome message
- `POST /crawl`: Submit URLs for crawling
  ```json
  {
    "urls": ["https://example.com"],
    "allowed_domains": ["example.com"],
    "depth": 2
  }
  ```
- `GET /job/{job_id}`: Get job status
- `POST /search`: Search indexed content
  ```json
  {
    "query": "your search query"
  }
  ```
- `GET /health`: Check system health

## Component Details

### Master Node

The master node manages job submissions, monitors system health, and provides API endpoints. It uses FastAPI to expose a RESTful API.

### Crawler Nodes

Crawler nodes poll the SQS queue for URLs to crawl. They use Scrapy to crawl websites and extract content, then send the content to the indexer queue.

### Indexer Nodes

Indexer nodes poll the SQS queue for content to index. They preprocess the content and index it in Elasticsearch, and store the indexed data in S3.

## Queue Structure

- `crawler-task-queue`: URLs to be crawled
- `indexer-task-queue`: Content to be indexed
- `monitoring-queue`: System monitoring messages

## S3 Storage Structure

- `raw/`: Raw content from crawled pages
- `index/`: Indexed content data
- `metadata/`: System metadata

## License

MIT

## Author

Your Name

