#!/usr/bin/env python3
"""
Indexer worker script for the distributed crawler-indexer system.
This script polls the SQS queue for content to index and then processes it.
"""
import os
import sys
import time

# Add the project root to the path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# Add the src directory to the Python path
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
sys.path.append(SRC_DIR)

print("Python path:", sys.path)

# Import the indexer
from src.indexer.indexer_node import run_indexer

if __name__ == "__main__":
    print("Starting indexer worker...")
    try:
        # Set the PYTHONPATH environment variable
        os.environ['PYTHONPATH'] = SRC_DIR
        run_indexer()
    except KeyboardInterrupt:
        print("Indexer worker stopped by user.")
    except Exception as e:
        print(f"Indexer worker stopped due to error: {e}")
        # Attempt to restart after a brief delay
        time.sleep(5)
        print("Attempting to restart indexer worker...")
        try:
            run_indexer()
        except Exception as e2:
            print(f"Failed to restart indexer worker: {e2}")
            sys.exit(1)