#!/usr/bin/env bash
# =============================================================
# Host Setup Script — Run once on the E2E Cloud C3 Node
# Sets up directories, permissions, and firewall rules
# =============================================================

set -euo pipefail

echo "=== VigyanPilot PostgreSQL Host Setup ==="

# 1. Create data directory with correct ownership
echo "[1/5] Creating PostgreSQL data directory..."
sudo mkdir -p /opt/vigyanpilot_pgdata
sudo chown 999:999 /opt/vigyanpilot_pgdata  # postgres container user UID
sudo chmod 700 /opt/vigyanpilot_pgdata

# 2. Create WAL archive directory
echo "[2/5] Creating WAL archive directory..."
sudo mkdir -p /opt/vigyanpilot_pgdata/wal_archive
sudo chown 999:999 /opt/vigyanpilot_pgdata/wal_archive

# 3. Create backup directory
echo "[3/5] Creating backup directory..."
sudo mkdir -p /opt/vigyanpilot_backups
sudo chown "$(id -u):$(id -g)" /opt/vigyanpilot_backups
sudo chmod 750 /opt/vigyanpilot_backups

# 4. Firewall: Block PostgreSQL port from public internet
echo "[4/5] Configuring UFW firewall rules..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
# Allow SSH
sudo ufw allow 22/tcp
# Allow HTTPS (FastAPI)
sudo ufw allow 443/tcp
# Allow HTTP for Let's Encrypt challenges
sudo ufw allow 80/tcp
# EXPLICITLY DENY PostgreSQL from public
sudo ufw deny 5432/tcp
# Show status
sudo ufw status verbose

# 5. Secure env files
echo "[5/5] Securing environment files..."
chmod 600 /opt/vigyanpilot/infra/.env.postgres 2>/dev/null || true
chmod 600 /opt/vigyanpilot/infra/.env.app 2>/dev/null || true

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Edit /opt/vigyanpilot/infra/.env.postgres with a real 64-char password"
echo "  2. Edit /opt/vigyanpilot/infra/.env.app with matching credentials"
echo "  3. Run: cd /opt/vigyanpilot/infra && docker compose up -d"
echo "  4. Set up the backup cron: crontab -e → add the daily backup line"
