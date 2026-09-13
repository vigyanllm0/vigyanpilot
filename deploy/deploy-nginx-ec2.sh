#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# VigyanLLM — Deploy nginx config + SSL for EC2
# Run ONCE on EC2: bash deploy/deploy-nginx-ec2.sh
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

EMAIL="contact@vigyanllm.in"
DOMAIN="vigyanllm.in"
WWW_DOMAIN="www.vigyanllm.in"

echo "=== Step 1: Install certbot if missing ==="
if ! command -v certbot &>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq certbot python3-certbot-nginx
fi

echo "=== Step 2: Get Let's Encrypt certificate ==="
# Stop nginx temporarily so certbot can use port 80
sudo systemctl stop nginx 2>/dev/null || true

# Get cert for both domains
sudo certbot certonly --standalone \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  -d "$DOMAIN" \
  -d "$WWW_DOMAIN"

echo "=== Step 3: Deploy nginx config ==="
sudo tee /etc/nginx/sites-available/vigyanllm.conf > /dev/null << 'NGINX_EOF'
# VigyanLLM — EC2 nginx config
# Bare domain → www redirect + CloudFront API proxy

# HTTP → HTTPS redirect (bare domain)
server {
    listen 80;
    server_name vigyanllm.in www.vigyanllm.in;
    return 301 https://www.vigyanllm.in$request_uri;
}

# HTTPS — bare domain → www redirect
server {
    listen 443 ssl http2;
    server_name vigyanllm.in;

    ssl_certificate /etc/letsencrypt/live/vigyanllm.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vigyanllm.in/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    return 301 https://www.vigyanllm.in$request_uri;
}

# HTTPS — www (receives API requests from CloudFront)
server {
    listen 443 ssl http2;
    server_name www.vigyanllm.in;

    ssl_certificate /etc/letsencrypt/live/vigyanllm.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vigyanllm.in/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    gzip on;
    gzip_types text/html text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1000;
    gzip_vary on;

    client_max_body_size 10M;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "0" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # CORS — allow both domains
    set $cors_origin "";
    if ($http_origin ~* "^https://(www\.)?vigyanllm\.in$") {
        set $cors_origin $http_origin;
    }
    add_header Access-Control-Allow-Origin $cors_origin always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
    add_header Access-Control-Allow-Credentials "true" always;

    # CMS proxy (port 8001)
    location /api/v1/cms/ {
        proxy_pass http://127.0.0.1:8001/api/v1/cms/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # All other requests → gunicorn
    location / {
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin $cors_origin;
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With";
            add_header Access-Control-Allow-Credentials "true";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        proxy_pass http://127.0.0.1:11436;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /health {
        proxy_pass http://127.0.0.1:11436;
        access_log off;
    }
}
NGINX_EOF

echo "=== Step 4: Enable site and reload nginx ==="
sudo ln -sf /etc/nginx/sites-available/vigyanllm.conf /etc/nginx/sites-enabled/vigyanllm.conf
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx

echo "=== Step 5: Set up auto-renewal ==="
echo "0 3 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" | sudo tee /etc/cron.d/certbot-renew

echo ""
echo "=== DONE! ==="
echo "Test: curl -I https://www.vigyanllm.in/health"
echo "Test: curl -I http://vigyanllm.in/ (should 301 → https://www.vigyanllm.in)"
