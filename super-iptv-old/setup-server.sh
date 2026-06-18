#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "============================================="
echo " IPTV Web Player Server Setup (Ubuntu 24.04) "
echo "============================================="

# Ensure script is run as root/sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo:"
  echo "sudo ./setup-server.sh"
  exit 1
fi

# Ask for domain or IP address
read -p "Enter your Domain Name or Server Public IP (e.g. 192.168.1.100): " SERVER_IP
if [ -z "$SERVER_IP" ]; then
  SERVER_IP="_"
fi

# Detect the non-root user who invoked sudo (to grant them folder permissions)
REAL_USER=${SUDO_USER:-$USER}

echo "--> Updating package index..."
apt-get update

echo "--> Installing Nginx..."
apt-get install nginx -y

echo "--> Installing Node.js..."
apt-get install nodejs -y

echo "--> Creating web directories..."
mkdir -p /var/www/super-iptv/dist

echo "--> Setting permissions for user: $REAL_USER..."
chown -R "$REAL_USER":"$REAL_USER" /var/www/super-iptv
chmod -R 755 /var/www/super-iptv

echo "--> Configuring Nginx for HTTP Only..."
cat <<EOF > /etc/nginx/sites-available/super-iptv
server {
    listen 80;
    server_name 107.174.178.52;

    root /var/www/super-iptv/dist;
    index index.html;

    # Proxy API requests to Node.js backend
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Handle single-page React app routing
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Compress assets
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Browser caching for static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|otf)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF

echo "--> Enabling IPTV configuration..."
if [ -f /etc/nginx/sites-enabled/default ]; then
  rm /etc/nginx/sites-enabled/default
fi

# Create symbolic link if it doesn't exist
if [ ! -f /etc/nginx/sites-enabled/super-iptv ]; then
  ln -s /etc/nginx/sites-available/super-iptv /etc/nginx/sites-enabled/
fi

echo "--> Configuring Systemd Service for API..."
cat <<EOF > /etc/systemd/system/super-iptv-api.service
[Unit]
Description=Super IPTV API Service
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=/var/www/super-iptv
ExecStart=/usr/bin/node server.js
Restart=on-failure
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

echo "--> Enabling and starting IPTV API service..."
systemctl daemon-reload
systemctl enable super-iptv-api
systemctl restart super-iptv-api || systemctl start super-iptv-api

echo "--> Testing and restarting Nginx..."
nginx -t
systemctl restart nginx

echo "--> Configuring Firewall (UFW) to allow HTTP only..."
ufw allow 'Nginx HTTP'
echo "Firewall configured. Note: Ensure port 22 (SSH) is also allowed if UFW was disabled before!"

echo "============================================="
echo " SETUP COMPLETED SUCCESSFULLY!"
echo "============================================="
echo "1. Web Root: /var/www/super-iptv/dist"
echo "2. Served at: http://107.174.178.52"
echo ""
echo "To authorize GitHub Actions to update this site:"
echo "-----------------------------------------------"
echo "1. On your local machine or server, run:"
echo "   ssh-keygen -t ed25519 -C \"github-actions\""
echo "2. Append the contents of '~/.ssh/id_ed25519.pub' to your server's file:"
echo "   /home/$REAL_USER/.ssh/authorized_keys"
echo "3. Go to GitHub -> Settings -> Secrets and variables -> Actions -> Secrets"
echo "4. Add the following secrets:"
echo "   - SSH_HOST : 107.174.178.52 (or your public IP)"
echo "   - SSH_USER : $REAL_USER"
echo "   - SSH_KEY  : (Copy the contents of your private key '~/.ssh/id_ed25519')"
echo "============================================="
