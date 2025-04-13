# Distributed-Crawler-Indexer
A scalable, fault-tolerant distributed web crawler designed for crawling, indexing, and searching web content across multiple nodes, all deployed on cloud VM.

---
## Features

- **Distributed Crawling** – Parallel crawling across nodes for efficiency.
- **Search Interface** – Simple search interface to query indexed data.
- **Indexing** – Indexing of crawled pages for fast retrieval.
- **Fault Tolerance** – Resilient design with retries and failover.
- **Monitoring Dashboard** – Real-time view of crawling and indexing progress.

---

## Architecture Overview

This project follows a modular microservice-based architecture:

- **Crawler Workers**: Fetch and parse web content.
- **Queue System**: Distributes tasks between crawler nodes.
- **Storage Layer**: Stores raw and processed data.
- **Indexer**: Builds searchable indexes.
- **Search API**: Serves user queries.
- **Monitoring & Logs**: Tracks task status and system health.

> See detailed [Architecture Docs](docs/architecture.md) for diagrams and flow.

---

## Technology Stack

- **Language**: Python 3.x
- **Cloud Provider**: AWS 
- **Key Libraries**:
  - `Scrapy` - Web Crawling
  - `Celery` – Task queues
- **Queue Service**: Redis
- **Storage**: S3
---

## Setup & Installation

### Prerequisites

- Python 3.8+
- Cloud credentials (AWS)

### Installation

```bash
# Clone the repo
git clone 
cd 

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration


---

## Usage

---

## Running Tests

---

## Contributing

No thanks.

