#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# VigyanLLM — SSL Setup for EC2 Backend
# Run this ONCE on the EC2 instance to get Let's Encrypt certificates.
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <domain>"
  echo "Example: $0 api.vigyanllm.in"
  exit 1
fi

DOMAIN="$1"
EMAIL="contact@vigyanllm.in"

echo "=== Installing certbot ==="
sudo apt-get update -qq
sudo apt-get install -y -qq certbot python3-certbot-nginx

echo "=== Stopping nginx temporarily (certbot needs port 80) ==="
sudo systemctl stop nginx 2>/dev/null || true

echo "=== Getting certificate for $DOMAIN ==="
sudo certbot certonly --standalone \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  -d "$DOMAIN"

echo "=== Updating nginx config ==="
sudo sed -i "s|/etc/ssl/certs/vigyan-selfsigned.crt|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /home/ubuntu/vigyanpilot/deploy/nginx.conf
sudo sed -i "s|/etc/ssl/private/vigyan-selfsigned.key|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /home/ubuntu/vigyanpilot/deploy/nginx.conf
sudo sed -i "s|server_name _;|server_name $DOMAIN;|g" /home/ubuntu/vigyanpilot/deploy/nginx.conf

echo "=== Starting nginx ==="
sudo systemctl start nginx

echo "=== Setting up auto-renewal ==="
echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" | sudo tee /etc/cron.d/certbot-renew

echo "=== Done! SSL active for $DOMAIN ==="
echo "Test: curl -I https://$DOMAIN/health"
