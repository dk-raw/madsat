#!/bin/bash
cd /home/nikolakis/madsat
echo "Pulling latest changes from GitHub..."
git pull origin main

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Restarting the application..."
sudo systemctl restart madsat.service
echo "Update complete!"
