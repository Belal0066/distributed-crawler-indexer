#!/usr/bin/env python3
"""
Indexer worker script for the distributed crawler-indexer system.
This script polls the SQS queue for content to index and then processes it.
"""
import os
import sys
import time
import importlib.metadata
import signal
import random

# Add the project root to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# Add the src directory to the Python path
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.append(SRC_DIR)

print("Python path:", sys.path)

# Check Elasticsearch client version
try:
    es_version = importlib.metadata.version("elasticsearch")
    print(f"Elasticsearch client version: {es_version}")
except importlib.metadata.PackageNotFoundError:
    print("Elasticsearch client not found. Please install it using: pip install elasticsearch")
    sys.exit(1)

# Import the indexer and fault tolerance
from src.indexer.indexer_node import run_indexer
from src.common.monitor import indexer_monitor

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

def indexer_loop():
    """Main indexer worker loop with error handling and recovery"""
    global shutdown_requested
    max_failures = 5
    failure_count = 0
    backoff_time = 1  # Initial backoff time in seconds
    
    # Start monitoring
    indexer_monitor.start()
    
    while not shutdown_requested:
        try:
            print("Running indexer worker cycle...")
            run_indexer(check_shutdown=lambda: shutdown_requested)
            # If we get here without errors, reset failure counters
            failure_count = 0
            backoff_time = 1
            time.sleep(1)  # Short pause between successful cycles
        except KeyboardInterrupt:
            print("Indexer worker stopped by user.")
            break
        except Exception as e:
            failure_count += 1
            print(f"Indexer worker error (attempt {failure_count}): {e}")
            
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

    print("Indexer worker shutdown complete.")

if __name__ == "__main__":
    print("Starting indexer worker...")
    try:
        # Set the PYTHONPATH environment variable
        os.environ['PYTHONPATH'] = SRC_DIR
        indexer_loop()
    except Exception as e:
        print(f"Unhandled exception in indexer worker: {e}")
        sys.exit(1)
