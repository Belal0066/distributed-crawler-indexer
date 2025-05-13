#!/usr/bin/env python3
"""
Crawler worker script for the distributed crawler-indexer system.
This script polls the SQS queue for URLs to crawl and then starts the crawlers.
"""
import os
import sys
import time

# Add the project root and src directory to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# Add the src directory to the Python path (for Scrapy to find the snipdex module)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.append(SRC_DIR)

print("Python path:", sys.path)

# Import the crawler worker runner
from src.snipdex.spiders.crawlerI import run_crawler_worker

if __name__ == "__main__":
    print("Starting crawler worker...")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Source directory added to path: {SRC_DIR}")
    try:
        os.environ['PYTHONPATH'] = SRC_DIR
        run_crawler_worker()
    except KeyboardInterrupt:
        print("Crawler worker stopped by user.")
    except Exception as e:
        print(f"Crawler worker stopped due to error: {e}")
        # Attempt to restart after a brief delay
        time.sleep(5)
        print("Attempting to restart crawler worker...")
        try:
            run_crawler_worker()
        except Exception as e2:
            print(f"Failed to restart crawler worker: {e2}")
            sys.exit(1) 