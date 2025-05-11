import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import boto3
import time
from config.aws_config import (
    AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
    MASTER_INSTANCE_TYPE, WORKER_INSTANCE_TYPE, KEY_NAME
)

def create_security_group(ec2):
    """Create a security group for the instances or use existing one."""
    security_group_name = 'crawler-indexer-sg'
    
    # Check if security group already exists
    try:
        response = ec2.describe_security_groups(
            Filters=[
                {
                    'Name': 'group-name',
                    'Values': [security_group_name]
                }
            ]
        )
        if response['SecurityGroups']:
            print(f"Security group '{security_group_name}' already exists. Using existing group.")
            return response['SecurityGroups'][0]['GroupId']
    except Exception as e:
        print(f"Error checking security group: {e}")
    
    # Create security group if it doesn't exist
    try:
        response = ec2.create_security_group(
            GroupName=security_group_name,
            Description='Security group for crawler-indexer system'
        )
        security_group_id = response['GroupId']
        
        # Allow SSH
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )
        
        # Allow internal communication
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 0,
                'ToPort': 65535,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )
        
        print(f"Created security group '{security_group_name}'")
        return security_group_id
    except Exception as e:
        print(f"Error creating security group: {e}")
        raise

def create_instance(ec2, instance_type, user_data, security_group_id):
    """Create an EC2 instance with the given configuration."""
    try:
        # Use a recent Ubuntu AMI for eu-north-1 region
        ami_id = 'ami-0989fb15ce71ba39e'  # Ubuntu 22.04 LTS in eu-north-1
        
        print(f"Creating {instance_type} instance...")
        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            KeyName=KEY_NAME,
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[security_group_id],
            UserData=user_data,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': f'crawler-indexer-{instance_type}'}]
            }]
        )
        instance = response['Instances'][0]
        print(f"Created instance {instance['InstanceId']}")
        return instance
    except Exception as e:
        print(f"Error creating instance: {e}")
        raise

def main():
    try:
        print("Initializing AWS clients...")
        # Initialize AWS clients
        ec2 = boto3.client('ec2',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # Create security group
        security_group_id = create_security_group(ec2)
        
        # Master node user data
        master_user_data = '''#!/bin/bash
apt-get update
apt-get install -y python3-pip git
git clone https://github.com/Belal0066/distributed-crawler-indexer.git
cd distributed-crawler-indexer
pip3 install -r requirements.txt
python3 src/master/master_node.py
'''
        
        # Worker node user data
        worker_user_data = '''#!/bin/bash
apt-get update
apt-get install -y python3-pip git
git clone https://github.com/Belal0066/distributed-crawler-indexer.git
cd distributed-crawler-indexer
pip3 install -r requirements.txt
python3 src/worker/worker_node.py
'''
        
        # Create instances
        print("Creating master instance...")
        master_instance = create_instance(
            ec2, MASTER_INSTANCE_TYPE, master_user_data, security_group_id
        )
        
        # Create worker instances
        print("Creating worker instances...")
        worker_instances = []
        for i in range(3):  # Create 3 worker instances
            worker_instance = create_instance(
                ec2, WORKER_INSTANCE_TYPE, worker_user_data, security_group_id
            )
            worker_instances.append(worker_instance)
        
        print("Deployment started. Waiting for instances to be ready...")
        
        # Wait for instances to be running
        instance_ids = [master_instance['InstanceId']] + [w['InstanceId'] for w in worker_instances]
        print(f"Waiting for instances to be running: {instance_ids}")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=instance_ids)
        
        # Get instance IPs
        instances = ec2.describe_instances(InstanceIds=instance_ids)
        print("\nDeployed instances:")
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_type = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unknown')
                print(f"Instance {instance['InstanceId']} ({instance_type}) is running at {instance.get('PublicIpAddress', 'N/A')}")
    
    except Exception as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 