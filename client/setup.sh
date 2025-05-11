#!/bin/bash
# Script to deploy the client web interface to the master node

# Node IP
MASTER_IP="13.61.185.63"

# Path to SSH key
KEY_FILE="/home/belal/Desktop/ASU/CSE354/repo2/distributed-crawler-indexer/test.pem"

# Make sure key has correct permissions
chmod 400 "$KEY_FILE"

# Create client directory on the master node
echo "Creating client directory on the master node..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "mkdir -p /home/ubuntu/crawler-indexer/client"

# Copy client files to the master node
echo "Copying client files to the master node..."
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no client/index.html client/styles.css client/app.js ubuntu@$MASTER_IP:/home/ubuntu/crawler-indexer/client/

# Set correct permissions
echo "Setting correct permissions..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "chmod -R 755 /home/ubuntu/crawler-indexer/client"

# Set up Nginx to serve the client files
echo "Setting up Nginx to serve the client files..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "sudo bash -c 'cat > /etc/nginx/sites-available/crawler-ui << EOL
server {
    listen 80;
    server_name _;
    
    # Serve static client files
    location / {
        root /home/ubuntu/crawler-indexer/client;
        index index.html;
        try_files \$uri \$uri/ =404;
    }
    
    # Proxy API requests to the backend
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOL'"

# Enable the Nginx site and restart Nginx
echo "Enabling Nginx site and restarting Nginx..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "sudo ln -sf /etc/nginx/sites-available/crawler-ui /etc/nginx/sites-enabled/ && sudo rm -f /etc/nginx/sites-enabled/default && sudo systemctl restart nginx"

# Verify Nginx configuration
echo "Verifying Nginx configuration..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "sudo nginx -t"

# Restart Nginx after verification
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "sudo systemctl restart nginx"

# Check Nginx status
echo "Checking Nginx status..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "sudo systemctl status nginx"

# List client files to verify deployment
echo "Verifying client files..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$MASTER_IP "ls -la /home/ubuntu/crawler-indexer/client/"

echo "Client UI deployment complete!"
echo "You can access the client UI at http://$MASTER_IP" 