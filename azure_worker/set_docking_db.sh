#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Set DOCKING_DATABASE_URL on EC2
# Run this on EC2 to configure the docking results database
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DB_URL="postgresql://docking_admin:VigyanDockDB2026!@vigyan-docking-db.postgres.database.azure.com/docking_db?sslmode=require"

# Add to .env if not present
if grep -q "DOCKING_DATABASE_URL" /home/ubuntu/vigyanpilot/.env 2>/dev/null; then
    sed -i "s|^DOCKING_DATABASE_URL=.*|DOCKING_DATABASE_URL=$DB_URL|" /home/ubuntu/vigyanpilot/.env
else
    echo "DOCKING_DATABASE_URL=$DB_URL" >> /home/ubuntu/vigyanpilot/.env
fi

echo "Updated .env with DOCKING_DATABASE_URL"
sudo systemctl restart vigyan
echo "Service restarted"
