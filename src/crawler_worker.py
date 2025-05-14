#!/usr/bin/env python3
"""
Crawler worker script for the distributed crawler-indexer system.
This script polls the SQS queue for URLs to crawl and then starts the crawlers.
"""
import os
import sys
import time
import threading
import signal
import random

# Add the project root and src directory to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# Add the src directory to the Python path (for Scrapy to find the snipdex module)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.append(SRC_DIR)

print("Python path:", sys.path)

# Import the crawler worker runner and fault tolerance
from src.snipdex.spiders.crawlerI import run_crawler_worker
from src.common.fault_tolerance import fault_manager
from src.common.monitor import crawler_monitor

# Flag to track if we're shutting down
shutdown_requested = False

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    print(f"Received shutdown signal {signum}, finishing current tasks...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def crawler_loop():
    """Main crawler worker loop with error handling and recovery"""
    global shutdown_requested
    max_failures = 5
    failure_count = 0
    backoff_time = 1  # Initial backoff time in seconds
    
    # Start monitoring and fault tolerance
    crawler_monitor.start()
    
    while not shutdown_requested:
        try:
            print("Running crawler worker cycle...")
            run_crawler_worker(check_shutdown=lambda: shutdown_requested)
            # If we get here without errors, reset failure counters
            failure_count = 0
            backoff_time = 1
            time.sleep(1)  # Short pause between successful cycles
        except KeyboardInterrupt:
            print("Crawler worker stopped by user.")
            break
        except Exception as e:
            failure_count += 1
            print(f"Crawler worker error (attempt {failure_count}): {e}")
            
            if failure_count >= max_failures:
                print(f"Too many failures ({failure_count}), pausing for longer recovery...")
                time.sleep(60)  # Longer pause after multiple failures
                failure_count = 0  # Reset after longer pause
            else:
                # Exponential backoff with jitter
                jitter = random.uniform(0, 0.1 * backoff_time)
                sleep_time = backoff_time + jitter
                print(f"Backing off for {sleep_time:.1f} seconds before retry...")
                time.sleep(sleep_time)
                backoff_time = min(backoff_time * 2, 30)  # Exponential backoff up to 30 seconds

    print("Crawler worker shutdown complete.")

if __name__ == "__main__":
    print("Starting crawler worker...")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Source directory added to path: {SRC_DIR}")
    
    try:
        os.environ['PYTHONPATH'] = SRC_DIR
        crawler_loop()
    except Exception as e:
        print(f"Unhandled exception in crawler worker: {e}")
        sys.exit(1) 