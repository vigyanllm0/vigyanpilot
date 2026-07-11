#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# VigyanLLM — AWS EC2 t3.micro Setup Script (Ubuntu 22.04 / Amazon Linux)
# ──────────────────────────────────────────────────────────────────────────

echo "=== Installing system dependencies ==="
sudo apt-get update -qq
sudo apt-get install -y -qq \
    docker.io \
    docker-compose-plugin \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    ufw

echo "=== Configuring firewall ==="
sudo ufw --force enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for certbot)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw status

echo "=== Starting Docker ==="
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu
newgrp docker || true

echo "=== Cloning repo ==="
cd /home/ubuntu
git clone https://github.com/vigyanllm0/vigyanpilot.git
cd vigyanpilot

echo "=== Creating .env file ==="
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# ── REQUIRED — Generated during setup, DO NOT COMMIT ──────────────
PRIMERFORGE_SECRET=CHANGE_ME_TO_64_CHAR_HEX_STRING
PRIMERFORGE_ADMIN_EMAIL=contact@vigyanllm.in
PRIMERFORGE_ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD
PGPASSWORD=CHANGE_ME_STRONG_PG_PASSWORD

# ── Razorpay (set these manually) ─────────────────────────────────
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx

# ── Google OAuth ──────────────────────────────────────────────────
GOOGLE_CLIENT_ID=xxxxxxxxxx.apps.googleusercontent.com

# ── Optional ──────────────────────────────────────────────────────
NCBI_API_KEY=

# ── Docking Results Database (Azure PostgreSQL) ──────────────────
# DOCKING_DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
ENVEOF
    echo "!!! .env created — you MUST edit it with real secrets: nano .env"
fi

echo "=== Setting up SSL with Let's Encrypt ==="
echo "Run this AFTER pointing your domain to this server's IP:"
echo "  sudo certbot --nginx -d api.vigyanllm.in"
echo ""
echo "For now, using self-signed cert for testing..."
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/vigyan-selfsigned.key \
    -out /etc/ssl/certs/vigyan-selfsigned.crt \
    -subj "/CN=vigyanllm-local" 2>/dev/null || true

# Update nginx.conf to use self-signed cert temporarily
sed -i 's|/etc/letsencrypt/live/api.vigyanllm.in/fullchain.pem|/etc/ssl/certs/vigyan-selfsigned.crt|g' deploy/nginx.conf
sed -i 's|/etc/letsencrypt/live/api.vigyanllm.in/privkey.pem|/etc/ssl/private/vigyan-selfsigned.key|g' deploy/nginx.conf

echo "=== Starting services ==="
cd deploy
sudo docker compose up --build -d

echo ""
echo "=== Setup Complete ==="
echo "Backend running on: https://<EC2_PUBLIC_IP>/"
echo ""
echo "Next steps:"
echo "  1. Edit .env with real secrets: nano /home/ubuntu/vigyanpilot/.env"
echo "  2. Restart after env changes: cd /home/ubuntu/vigyanpilot/deploy && sudo docker compose up -d"
echo "  3. Set up domain + SSL: sudo certbot --nginx -d api.vigyanllm.in"
echo "  4. Verify by visiting https://vigyanllm.in/health"
echo ""
