import boto3
import json
import time
import socket
import uuid
import threading
from datetime import datetime
from .aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    MONITORING_QUEUE_NAME
)

# Initialize SQS client
sqs = boto3.client('sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Get monitoring queue URL
try:
    response = sqs.get_queue_url(QueueName=MONITORING_QUEUE_NAME)
    MONITORING_QUEUE_URL = response['QueueUrl']
except Exception as e:
    print(f"Error getting monitoring queue URL: {e}")
    MONITORING_QUEUE_URL = None

# Generate a unique node ID
NODE_ID = f"{socket.gethostname()}-{uuid.uuid4()}"

class NodeMonitor:
    def __init__(self, node_type, heartbeat_interval=30):
        """
        Initialize the node monitor
        
        Args:
            node_type (str): Type of node ('master', 'crawler', 'indexer')
            heartbeat_interval (int): Heartbeat interval in seconds
        """
        self.node_type = node_type
        self.node_id = NODE_ID
        self.heartbeat_interval = heartbeat_interval
        self.running = False
        self.metrics = {
            'tasks_processed': 0,
            'errors': 0,
            'start_time': time.time()
        }
        self.heartbeat_thread = None
    
    def start(self):
        """
        Start the heartbeat thread
        """
        if self.running:
            return
        
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        print(f"Started monitoring for node {self.node_id} ({self.node_type})")
    
    def stop(self):
        """
        Stop the heartbeat thread
        """
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        print(f"Stopped monitoring for node {self.node_id}")
    
    def _heartbeat_loop(self):
        """
        Main heartbeat loop
        """
        while self.running:
            try:
                self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"Error in heartbeat loop: {e}")
                time.sleep(5)  # Shorter interval after error
    
    def send_heartbeat(self):
        """
        Send a heartbeat message to the monitoring queue
        """
        if not MONITORING_QUEUE_URL:
            print("Monitoring queue URL not available. Skipping heartbeat.")
            return
        
        # Create heartbeat message
        heartbeat = {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'status': 'active'
        }
        
        # Send message to queue
        try:
            response = sqs.send_message(
                QueueUrl=MONITORING_QUEUE_URL,
                MessageBody=json.dumps(heartbeat)
            )
            return response
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
    
    def update_metric(self, metric_name, value):
        """
        Update a monitoring metric
        """
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
        else:
            self.metrics[metric_name] = value

def check_node_health(node_id=None, max_age=60):
    """
    Check the health of a node or all nodes
    
    Args:
        node_id (str, optional): Node ID to check. If None, check all nodes.
        max_age (int): Maximum message age in seconds
    
    Returns:
        dict: Node health information
    """
    if not MONITORING_QUEUE_URL:
        return {'status': 'error', 'error': 'Monitoring queue URL not available'}
    
    try:
        # Receive messages from queue
        response = sqs.receive_message(
            QueueUrl=MONITORING_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=1
        )
        
        messages = response.get('Messages', [])
        
        # Process messages
        nodes = {}
        current_time = time.time()
        
        for message in messages:
            try:
                body = json.loads(message['Body'])
                msg_node_id = body.get('node_id')
                
                # Skip if we're looking for a specific node and this isn't it
                if node_id and msg_node_id != node_id:
                    continue
                
                timestamp = body.get('timestamp')
                if timestamp:
                    msg_time = datetime.fromisoformat(timestamp).timestamp()
                    age = current_time - msg_time
                    
                    # Only consider recent messages
                    if age <= max_age:
                        nodes[msg_node_id] = {
                            'node_type': body.get('node_type'),
                            'last_seen': timestamp,
                            'age': age,
                            'status': body.get('status'),
                            'metrics': body.get('metrics', {})
                        }
                
                # Leave message in queue for others to see
                # Do not delete heartbeat messages
            except Exception as e:
                print(f"Error processing message: {e}")
        
        # Check if we found the node we're looking for
        if node_id and node_id not in nodes:
            return {
                'status': 'error',
                'error': f'Node {node_id} not found or heartbeat too old',
                'node_id': node_id
            }
        
        return {
            'status': 'success',
            'nodes': nodes,
            'count': len(nodes)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Create default monitors
master_monitor = NodeMonitor('master')
crawler_monitor = NodeMonitor('crawler')
indexer_monitor = NodeMonitor('indexer') 