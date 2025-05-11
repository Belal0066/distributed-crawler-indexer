#!/bin/bash
# Script to fix services on all deployed instances

# Update these with your instance IPs
MASTER_IP="13.60.242.212"
INDEXER_IP="13.61.18.116"
CRAWLER1_IP="16.170.143.198"
CRAWLER2_IP="51.20.108.54"

# Update with the path to your key file
KEY_FILE='/home/belal/Desktop/ASU/CSE354/repo2/distributed-crawler-indexer/test.pem' #"$HOME/.ssh/aws-ec2.pem"

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
  echo "Key file not found: $KEY_FILE"
  echo "Please specify the correct path to your key file."
  exit 1
fi

# Make sure key file has correct permissions
chmod 400 "$KEY_FILE"

# Function to run a command on a remote host
run_command() {
  local host="$1"
  local description="$2"
  local command="$3"
  
  echo "=== $description on $host ==="
  ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$host "$command"
  echo ""
}

echo "Fixing services on all instances..."

# Fix Master Node service
echo "Fixing Master Node at $MASTER_IP..."
run_command "$MASTER_IP" "Update master-node service" "sudo bash -c 'cat > /etc/systemd/system/master-node.service << EOL
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
EOL'"

run_command "$MASTER_IP" "Reload systemd and restart service" "sudo systemctl daemon-reload && sudo systemctl restart master-node.service"
run_command "$MASTER_IP" "Check service status" "sudo systemctl status master-node.service"

# Fix Crawler1 Node service
echo "Fixing Crawler1 Node at $CRAWLER1_IP..."
run_command "$CRAWLER1_IP" "Update crawler-worker service" "sudo bash -c 'cat > /etc/systemd/system/crawler-worker.service << EOL
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
EOL'"

run_command "$CRAWLER1_IP" "Reload systemd and restart service" "sudo systemctl daemon-reload && sudo systemctl restart crawler-worker.service"
run_command "$CRAWLER1_IP" "Check service status" "sudo systemctl status crawler-worker.service"

# Fix Crawler2 Node service
echo "Fixing Crawler2 Node at $CRAWLER2_IP..."
run_command "$CRAWLER2_IP" "Update crawler-worker service" "sudo bash -c 'cat > /etc/systemd/system/crawler-worker.service << EOL
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
EOL'"

run_command "$CRAWLER2_IP" "Reload systemd and restart service" "sudo systemctl daemon-reload && sudo systemctl restart crawler-worker.service"
run_command "$CRAWLER2_IP" "Check service status" "sudo systemctl status crawler-worker.service"

# Fix Indexer Node service
echo "Fixing Indexer Node at $INDEXER_IP..."
run_command "$INDEXER_IP" "Update indexer-worker service" "sudo bash -c 'cat > /etc/systemd/system/indexer-worker.service << EOL
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
EOL'"

run_command "$INDEXER_IP" "Reload systemd and restart service" "sudo systemctl daemon-reload && sudo systemctl restart indexer-worker.service"
run_command "$INDEXER_IP" "Check service status" "sudo systemctl status indexer-worker.service"

echo "All services fixed. Try accessing the master node API again at http://$MASTER_IP:8000" 