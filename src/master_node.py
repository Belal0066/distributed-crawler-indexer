#!/usr/bin/env python3
"""
Master node script for the distributed crawler-indexer system.
This script starts both the master node worker and the API server.
"""
import os
import sys
import multiprocessing
import time
import signal
import uvicorn

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the master node
from src.master.master_node import MasterNode

# Global flag to control the API server process
running = True

def run_api_server():
    """Run the FastAPI server"""
    try:
        uvicorn.run(
            "src.master.api:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=False
        )
    except Exception as e:
        print(f"API server error: {e}")

def run_master_node():
    """Run the master node worker"""
    try:
        master = MasterNode()
        print("Master Node started. Ready to process tasks.")
        
        # Keep the process running
        while running:
            time.sleep(1)
    except Exception as e:
        print(f"Master Node error: {e}")

def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM signals"""
    global running
    print("Shutting down...")
    running = False
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start API server in a separate process
    api_process = multiprocessing.Process(target=run_api_server)
    api_process.start()
    print(f"API server started on http://0.0.0.0:8000")
    
    # Run master node in the main process
    try:
        run_master_node()
    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        if api_process.is_alive():
            api_process.terminate()
            api_process.join(timeout=5)
        
        print("Master node stopped.") 