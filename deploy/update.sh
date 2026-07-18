#!/bin/bash
# Update script - pull latest changes from GitHub
# Run: sudo bash update.sh

set -e

APP_DIR="/var/www/ubuntu-zipgrade"

echo "==> Pulling latest changes..."
cd /home/icts/ai-exam-checker/ai-exam-checker
git pull origin main

echo "==> Copying updated files..."
cp -r ../frontend $APP_DIR/frontend
cp -r ../backend $APP_DIR/backend

# Restore config.js (not in git)
if [ -f "$APP_DIR/frontend/config.js" ]; then
  echo "==> config.js preserved."
else
  echo "WARNING: config.js missing! Copy it manually to $APP_DIR/frontend/config.js"
fi

echo "==> Installing any new dependencies..."
$APP_DIR/venv/bin/pip install -r $APP_DIR/backend/requirements.txt

echo "==> Restarting service..."
systemctl restart ubuntu-zipgrade

echo ""
echo "==> Done! Status:"
systemctl status ubuntu-zipgrade --no-pager
