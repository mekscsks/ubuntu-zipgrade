#!/bin/bash
# ubuntu-zipgrade - Ubuntu Deployment Script
# Run as root: sudo bash deploy.sh

set -e

APP_DIR="/var/www/ubuntu-zipgrade"
LOG_DIR="/var/log/ubuntu-zipgrade"

echo "==> Installing system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv nginx libzbar0 certbot python3-certbot-nginx

echo "==> Creating app directory..."
mkdir -p $APP_DIR $LOG_DIR
chown -R www-data:www-data $LOG_DIR

echo "==> Copying project files..."
cp -r ../backend $APP_DIR/backend
cp -r ../frontend $APP_DIR/frontend

echo "==> Setting up Python virtual environment..."
python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install --upgrade pip
$APP_DIR/venv/bin/pip install gunicorn
$APP_DIR/venv/bin/pip install -r $APP_DIR/backend/requirements.txt

echo "==> Copying .env file..."
# Make sure to place your .env file in the backend folder before running this
if [ ! -f "$APP_DIR/backend/.env" ]; then
    echo "WARNING: .env file not found! Copy your .env to $APP_DIR/backend/.env"
fi

echo "==> Setting up Nginx..."
cp nginx.conf /etc/nginx/sites-available/ubuntu-zipgrade
ln -sf /etc/nginx/sites-available/ubuntu-zipgrade /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> Setting up systemd service..."
cp ubuntu-zipgrade.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ubuntu-zipgrade
systemctl start ubuntu-zipgrade

echo ""
echo "==> Done! Status:"
systemctl status ubuntu-zipgrade --no-pager

echo ""
echo "==> (Optional) Enable HTTPS with Let's Encrypt:"
echo "    certbot --nginx -d your-domain.com"
