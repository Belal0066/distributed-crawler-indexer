#!/usr/bin/env python3
"""
Crawler worker script for the distributed crawler-indexer system.
This script polls the SQS queue for URLs to crawl and then starts the crawlers.
"""
import os
import sys
import time

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the crawler worker runner
from src.snipdex.spiders.crawlerI import run_crawler_worker

if __name__ == "__main__":
    print("Starting crawler worker...")
    try:
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