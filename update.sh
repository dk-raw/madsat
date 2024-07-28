#!/bin/bash
cd /home/nikolakis/madsat
echo "Pulling latest changes from GitHub..."
git pull origin main
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo "Restarting the application..."
sudo systemctl restart madsat.service
echo "Update complete!"
