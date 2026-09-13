#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────
# VigyanLLM — EC2 nginx config (HTTP-only, no SSL needed)
# CloudFront handles SSL. EC2 does bare→www redirect + API proxy.
# Run ONCE on EC2: bash deploy/deploy-nginx-ec2.sh
# ──────────────────────────────────────────────────────────────────────────
set -euo pipefail

echo "=== Step 1: Deploy nginx config ==="
sudo tee /etc/nginx/sites-available/vigyanllm.conf > /dev/null << 'NGINX_EOF'
# VigyanLLM — EC2 nginx (HTTP only, CloudFront handles SSL)

server {
    listen 80;
    server_name vigyanllm.in;

    # Bare domain → www redirect (over HTTP, no SSL needed)
    return 301 https://www.vigyanllm.in$request_uri;
}

server {
    listen 80;
    server_name www.vigyanllm.in;

    server_tokens off;

    gzip on;
    gzip_types text/html text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1000;
    gzip_vary on;

    client_max_body_size 10M;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "0" always;

    # CORS — allow both domains
    set $cors_origin "";
    if ($http_origin ~* "^https://(www\.)?vigyanllm\.in$") {
        set $cors_origin $http_origin;
    }
    add_header Access-Control-Allow-Origin $cors_origin always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE" always;
    add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
    add_header Access-Control-Allow-Credentials "true" always;

    # CMS proxy (port 8001) — localhost only
    location /api/v1/cms/ {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8001/api/v1/cms/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block direct access to admin pages — auth is client-side only
    location ~ ^/(admin|admin-reviews|cms-admin) {
        return 403;
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

echo "=== Step 2: Enable site and reload ==="
sudo ln -sf /etc/nginx/sites-available/vigyanllm.conf /etc/nginx/sites-enabled/vigyanllm.conf
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=== DONE! No SSL needed on EC2 — CloudFront handles it ==="
echo "Test: curl -I http://vigyanllm.in/ (should 301 → https://www.vigyanllm.in)"
echo "Test: curl -I http://www.vigyanllm.in/health"
