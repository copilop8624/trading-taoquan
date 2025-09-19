#!/bin/bash
# Quick VPS Deployment Script

echo "🚀 Trading Optimization App - VPS Deployment"
echo "=============================================="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y

# Clone repository (replace with your repo)
read -p "Enter your GitHub repo URL: " REPO_URL
git clone $REPO_URL trading-app
cd trading-app

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# Install PM2 for process management
sudo npm install -g pm2

# Create PM2 ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'trading-app',
    script: 'python',
    args: 'web_app.py',
    cwd: '$(pwd)',
    interpreter: '$(pwd)/.venv/bin/python',
    env: {
      'NODE_ENV': 'production',
      'PORT': 5000
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
};
EOF

# Start application
pm2 start ecosystem.config.js
pm2 startup
pm2 save

# Setup firewall
sudo ufw allow 22
sudo ufw allow 5000
sudo ufw --force enable

echo "✅ Deployment complete!"
echo "🌐 Access your app at: http://YOUR_VPS_IP:5000"
echo "📊 Monitor with: pm2 monit"