#!/bin/bash
# Script to check the status of the master node

MASTER_IP="13.60.242.212"
KEY_FILE='/home/belal/Desktop/ASU/CSE354/repo2/distributed-crawler-indexer/test.pem' #"$HOME/.ssh/aws-ec2.pem"


# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
  echo "Key file not found: $KEY_FILE"
  echo "Please specify the correct path to your key file."
  exit 1
fi

# Make sure key file has correct permissions
chmod 400 "$KEY_FILE"

# Function to run a command on the master node
run_command() {
  echo "=== $1 ==="
  ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "$2"
  echo ""
}

echo "Connecting to Master Node at $MASTER_IP..."

# Check if the host is reachable
if ! ping -c 1 $MASTER_IP &> /dev/null; then
  echo "Cannot reach host $MASTER_IP. Please check if the instance is running."
  exit 1
fi

# Check system status
run_command "System Info" "uname -a && uptime"
run_command "Disk Usage" "df -h"
run_command "Memory Usage" "free -h"

# Check if the code was deployed
run_command "Check Repository" "ls -la /home/ubuntu/crawler-indexer"

# Check master-node service status
run_command "Master Node Service Status" "sudo systemctl status master-node.service"

# Check service logs
run_command "Service Logs" "sudo journalctl -u master-node.service --no-pager -n 50"

# Check if the service is listening on port 8000
run_command "Network Connections" "sudo netstat -tulpn | grep 8000"

# Check AWS credentials
run_command "AWS Environment Variables" "grep -i AWS /home/ubuntu/.bashrc"

# Check python installation
run_command "Python Version" "python3 --version && pip3 list | grep -E 'boto3|fastapi|uvicorn'"

echo "Checks completed." 