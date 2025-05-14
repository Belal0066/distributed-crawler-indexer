import boto3
import json
import time
from datetime import datetime, timedelta
import threading
import random
from .aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    CRAWL_QUEUE_NAME, INDEXER_QUEUE_NAME, MONITORING_QUEUE_NAME
)
from .monitor import check_node_health

# Initialize SQS client
sqs = boto3.client('sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Get queue URLs
try:
    crawler_response = sqs.get_queue_url(QueueName=CRAWL_QUEUE_NAME)
    CRAWLER_QUEUE_URL = crawler_response['QueueUrl']
    
    indexer_response = sqs.get_queue_url(QueueName=INDEXER_QUEUE_NAME)
    INDEXER_QUEUE_URL = indexer_response['QueueUrl']
    
    monitoring_response = sqs.get_queue_url(QueueName=MONITORING_QUEUE_NAME)
    MONITORING_QUEUE_URL = monitoring_response['QueueUrl']
except Exception as e:
    print(f"Error getting queue URLs: {e}")

class FaultToleranceManager:
    def __init__(self, 
                node_timeout=120, 
                task_timeout=300, 
                check_interval=30, 
                replication_factor=2):
        """
        Initialize the fault tolerance manager
        
        Args:
            node_timeout (int): Node timeout in seconds (default: 120)
            task_timeout (int): Task timeout in seconds (default: 300)
            check_interval (int): Check interval in seconds (default: 30)
            replication_factor (int): Desired data replication factor (default: 2)
        """
        self.node_timeout = node_timeout
        self.task_timeout = task_timeout
        self.check_interval = check_interval
        self.replication_factor = replication_factor
        self.running = False
        self.thread = None
        self.last_check = {}  # Last time each node was seen
        self.task_assignments = {}  # Track task assignments: task_id -> node_id
        self.task_timestamps = {}  # Track when tasks were assigned: task_id -> timestamp
    
    def start(self):
        """Start the fault tolerance monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Started fault tolerance monitoring")
    
    def stop(self):
        """Stop the fault tolerance monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Stopped fault tolerance monitoring")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Check for node failures
                self._check_node_health()
                # Check for task timeouts
                self._check_task_timeouts()
                # Update replication as needed
                self._check_replication()
                
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in fault tolerance monitoring loop: {e}")
                time.sleep(5)  # Shorter interval after error
    
    def _check_node_health(self):
        """Check for node failures and handle accordingly"""
        print("Checking node health...")
        health_data = check_node_health(max_age=self.node_timeout)
        
        if health_data['status'] != 'success':
            print(f"Error checking node health: {health_data.get('error')}")
            return
        
        # Get current nodes
        active_nodes = health_data.get('nodes', {})
        current_time = time.time()
        
        # Check for nodes that have disappeared
        for node_id, last_seen in self.last_check.items():
            if node_id not in active_nodes:
                # Node has disappeared
                time_since_last = current_time - last_seen
                if time_since_last > self.node_timeout:
                    print(f"Node {node_id} has failed (not seen for {time_since_last:.1f} seconds)")
                    self._handle_node_failure(node_id)
        
        # Update last seen timestamps
        for node_id, data in active_nodes.items():
            if 'last_seen' in data:
                try:
                    timestamp = datetime.fromisoformat(data['last_seen']).timestamp()
                    self.last_check[node_id] = timestamp
                except ValueError:
                    self.last_check[node_id] = current_time
    
    def _handle_node_failure(self, node_id):
        """Handle a node failure"""
        print(f"Handling failure of node {node_id}")
        
        # Find tasks assigned to this node
        tasks_to_reassign = []
        for task_id, assigned_node in self.task_assignments.items():
            if assigned_node == node_id:
                tasks_to_reassign.append(task_id)
                print(f"Task {task_id} needs reassignment from failed node {node_id}")
        
        # Reassign tasks
        for task_id in tasks_to_reassign:
            self._reassign_task(task_id)
    
    def _reassign_task(self, task_id):
        """Reassign a task that was assigned to a failed node"""
        # Remove from tracking
        if task_id in self.task_assignments:
            del self.task_assignments[task_id]
        
        if task_id in self.task_timestamps:
            del self.task_timestamps[task_id]
        
        # The task should already be back in the queue due to
        # visibility timeout, so no need to explicitly requeue
        print(f"Task {task_id} marked for reassignment")
    
    def _check_task_timeouts(self):
        """Check for task timeouts"""
        current_time = time.time()
        timed_out_tasks = []
        
        for task_id, timestamp in self.task_timestamps.items():
            if current_time - timestamp > self.task_timeout:
                print(f"Task {task_id} has timed out")
                timed_out_tasks.append(task_id)
        
        # Handle timed out tasks
        for task_id in timed_out_tasks:
            self._reassign_task(task_id)
    
    def _check_replication(self):
        """Check and update data replication as needed"""
        # This would need to query the index to find documents with insufficient replicas
        # For now, just log that we're checking
        print("Checking data replication...")
    
    def register_task(self, task_id, node_id):
        """Register a task as being worked on by a specific node"""
        self.task_assignments[task_id] = node_id
        self.task_timestamps[task_id] = time.time()
        print(f"Registered task {task_id} to node {node_id}")
    
    def complete_task(self, task_id):
        """Mark a task as completed"""
        if task_id in self.task_assignments:
            del self.task_assignments[task_id]
        
        if task_id in self.task_timestamps:
            del self.task_timestamps[task_id]
        
        print(f"Task {task_id} marked as completed")
    
    def get_status(self):
        """Get the current fault tolerance status"""
        return {
            'active': self.running,
            'monitored_nodes': len(self.last_check),
            'active_tasks': len(self.task_assignments),
            'node_timeout': self.node_timeout,
            'task_timeout': self.task_timeout,
            'replication_factor': self.replication_factor
        }

# Create a global instance
fault_manager = FaultToleranceManager()
