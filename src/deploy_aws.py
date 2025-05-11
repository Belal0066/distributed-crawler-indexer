#!/usr/bin/env python3
"""
Deployment script for the distributed crawler-indexer system on AWS EC2.
This script sets up the necessary EC2 instances and deploys the code.
"""
import boto3
import argparse
import time
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AWS configuration
from src.common.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    init_sqs_queues, init_s3_bucket
)

# Default EC2 configuration
DEFAULT_AMI = 'ami-0989fb15ce71ba39e'  # Ubuntu 22.04 for eu-north-1
DEFAULT_INSTANCE_TYPE = 't3.micro'
DEFAULT_KEY_NAME = 'test'  # Key pair name in AWS (without .pem extension)
SECURITY_GROUP_NAME = 'crawler-indexer-sg'

# User data script for instance initialization
BASE_USER_DATA = """#!/bin/bash
apt-get update
apt-get install -y python3-pip git nginx
pip3 install boto3 fastapi uvicorn elasticsearch scrapy nltk celery[sqs]
git clone -b new_branch {repo_url} /home/ubuntu/crawler-indexer
chown -R ubuntu:ubuntu /home/ubuntu/crawler-indexer
"""

# Additional user data for master node
MASTER_USER_DATA = """
# Set environment variables
echo 'export AWS_REGION="{aws_region}"' >> /home/ubuntu/.bashrc
echo 'export AWS_ACCESS_KEY_ID="{aws_access_key}"' >> /home/ubuntu/.bashrc
echo 'export AWS_SECRET_ACCESS_KEY="{aws_secret_key}"' >> /home/ubuntu/.bashrc

# Create systemd service for master node
cat > /etc/systemd/system/master-node.service << 'EOL'
[Unit]
Description=Master Node for Crawler-Indexer
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/crawler-indexer
ExecStart=/usr/bin/python3 /home/ubuntu/crawler-indexer/src/master_node.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl enable master-node.service
systemctl start master-node.service
"""

# Additional user data for crawler node
CRAWLER_USER_DATA = """
# Set environment variables
echo 'export AWS_REGION="{aws_region}"' >> /home/ubuntu/.bashrc
echo 'export AWS_ACCESS_KEY_ID="{aws_access_key}"' >> /home/ubuntu/.bashrc
echo 'export AWS_SECRET_ACCESS_KEY="{aws_secret_key}"' >> /home/ubuntu/.bashrc

# Create systemd service for crawler worker
cat > /etc/systemd/system/crawler-worker.service << 'EOL'
[Unit]
Description=Crawler Worker for Crawler-Indexer
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/crawler-indexer
ExecStart=/usr/bin/python3 /home/ubuntu/crawler-indexer/src/crawler_worker.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl enable crawler-worker.service
systemctl start crawler-worker.service
"""

# Additional user data for indexer node
INDEXER_USER_DATA = """
# Set environment variables
echo 'export AWS_REGION="{aws_region}"' >> /home/ubuntu/.bashrc
echo 'export AWS_ACCESS_KEY_ID="{aws_access_key}"' >> /home/ubuntu/.bashrc
echo 'export AWS_SECRET_ACCESS_KEY="{aws_secret_key}"' >> /home/ubuntu/.bashrc

# Install Elasticsearch
apt-get install -y openjdk-11-jre-headless
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-7.x.list
apt-get update
apt-get install -y elasticsearch

# Configure Elasticsearch
cat > /etc/elasticsearch/elasticsearch.yml << 'EOL'
network.host: 0.0.0.0
discovery.type: single-node
EOL

# Enable and start Elasticsearch
systemctl enable elasticsearch.service
systemctl start elasticsearch.service

# Create systemd service for indexer worker
cat > /etc/systemd/system/indexer-worker.service << 'EOL'
[Unit]
Description=Indexer Worker for Crawler-Indexer
After=network.target elasticsearch.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/crawler-indexer
ExecStart=/usr/bin/python3 /home/ubuntu/crawler-indexer/src/indexer_worker.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
systemctl enable indexer-worker.service
systemctl start indexer-worker.service
"""

def create_security_group(ec2):
    """Create a security group for the instances"""
    try:
        # Check if security group already exists
        security_groups = ec2.describe_security_groups(
            Filters=[{'Name': 'group-name', 'Values': [SECURITY_GROUP_NAME]}]
        )['SecurityGroups']
        
        if security_groups:
            print(f"Security group '{SECURITY_GROUP_NAME}' already exists. Using existing group.")
            return security_groups[0]['GroupId']
        
        # Create new security group
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description='Security group for crawler-indexer system'
        )
        
        security_group_id = response['GroupId']
        
        # Add inbound rules
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                # SSH
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # HTTP
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # HTTPS
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # API
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 8000,
                    'ToPort': 8000,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # Elasticsearch
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 9200,
                    'ToPort': 9200,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                # Internal traffic between instances
                {
                    'IpProtocol': '-1',  # All protocols
                    'UserIdGroupPairs': [{'GroupId': security_group_id}]
                }
            ]
        )
        
        print(f"Created security group: {security_group_id}")
        return security_group_id
    except Exception as e:
        print(f"Error creating security group: {e}")
        raise

def create_instance(ec2, name, node_type, security_group_id, user_data, instance_type=DEFAULT_INSTANCE_TYPE):
    """Create an EC2 instance"""
    try:
        print(f"Creating {instance_type} instance...")
        response = ec2.run_instances(
            ImageId=DEFAULT_AMI,
            InstanceType=instance_type,
            KeyName=DEFAULT_KEY_NAME,
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[security_group_id],
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': name}
                    ]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        print(f"Created instance {instance_id} ({name})")
        return instance_id
    except Exception as e:
        print(f"Error creating instance: {e}")
        raise

def deploy_aws(repo_url, master_count=1, crawler_count=2, indexer_count=1):
    """
    Deploy the crawler-indexer system on AWS EC2
    
    Args:
        repo_url (str): URL of the Git repository
        master_count (int): Number of master nodes to create
        crawler_count (int): Number of crawler nodes to create
        indexer_count (int): Number of indexer nodes to create
    """
    # Initialize AWS clients
    print("Initializing AWS clients...")
    ec2 = boto3.client('ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Initialize SQS queues and S3 bucket
    init_sqs_queues()
    init_s3_bucket()
    
    # Create security group
    security_group_id = create_security_group(ec2)
    
    # Prepare user data scripts
    formatted_master_data = BASE_USER_DATA.format(repo_url=repo_url) + MASTER_USER_DATA.format(
        aws_region=AWS_REGION,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_key=AWS_SECRET_ACCESS_KEY
    )
    
    formatted_crawler_data = BASE_USER_DATA.format(repo_url=repo_url) + CRAWLER_USER_DATA.format(
        aws_region=AWS_REGION,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_key=AWS_SECRET_ACCESS_KEY
    )
    
    formatted_indexer_data = BASE_USER_DATA.format(repo_url=repo_url) + INDEXER_USER_DATA.format(
        aws_region=AWS_REGION,
        aws_access_key=AWS_ACCESS_KEY_ID,
        aws_secret_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Create instances
    instance_ids = []
    
    # Create master nodes
    print("Creating master instance...")
    for i in range(master_count):
        instance_id = create_instance(
            ec2, 
            f"Master{i+1}", 
            "master",
            security_group_id, 
            formatted_master_data
        )
        instance_ids.append(instance_id)
    
    # Create crawler nodes
    print("Creating crawler instances...")
    for i in range(crawler_count):
        instance_id = create_instance(
            ec2, 
            f"Crawler{i+1}", 
            "crawler",
            security_group_id, 
            formatted_crawler_data
        )
        instance_ids.append(instance_id)
    
    # Create indexer nodes
    print("Creating indexer instances...")
    for i in range(indexer_count):
        instance_id = create_instance(
            ec2, 
            f"Indexer{i+1}", 
            "indexer",
            security_group_id, 
            formatted_indexer_data
        )
        instance_ids.append(instance_id)
    
    # Wait for instances to be running
    print("Deployment started. Waiting for instances to be ready...")
    print(f"Waiting for instances to be running: {instance_ids}")
    
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=instance_ids)
    
    # Get instance information
    response = ec2.describe_instances(InstanceIds=instance_ids)
    
    print("\nDeployed instances:")
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            public_ip = instance.get('PublicIpAddress', 'N/A')
            
            # Get the Name tag
            name = 'crawler-indexer'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            
            print(f"Instance {instance_id} ({name}) is running at {public_ip}")
    
    print("\nDeployment complete!")
    print("Note: It may take a few minutes for the instances to complete initialization.")
    print("You can access the master node API at http://<master-ip>:8000")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Deploy crawler-indexer system on AWS EC2')
    parser.add_argument('--repo-url', type=str, default='https://github.com/Belal0066/distributed-crawler-indexer.git',
                        help='URL of the Git repository')
    parser.add_argument('--master-count', type=int, default=1,
                        help='Number of master nodes to create')
    parser.add_argument('--crawler-count', type=int, default=2,
                        help='Number of crawler nodes to create')
    parser.add_argument('--indexer-count', type=int, default=1,
                        help='Number of indexer nodes to create')
    
    args = parser.parse_args()
    
    deploy_aws(
        repo_url=args.repo_url,
        master_count=args.master_count,
        crawler_count=args.crawler_count,
        indexer_count=args.indexer_count
    ) 