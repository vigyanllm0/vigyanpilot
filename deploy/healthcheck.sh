#!/usr/bin/env bash
# Health-check script for VigyanLLM backend
# Runs every 5 min via cron; restarts vigyan.service if unhealthy.
#
# Install in crontab:
#   sudo crontab -e
#   */5 * * * * /home/ubuntu/vigyanpilot/deploy/healthcheck.sh
#
# Usage: ./deploy/healthcheck.sh [url] [expected_keyword]

set -euo pipefail

LOGFILE=/var/log/vigyan-healthcheck.log
URL="${1:-http://127.0.0.1:5000/health}"
EXPECTED="${2:-ok}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"
}

# Check health endpoint
RESP=$(curl -s --max-time 10 "$URL" 2>/dev/null || echo "FAIL")
if [ "$RESP" = "FAIL" ] || ! echo "$RESP" | grep -qi "$EXPECTED"; then
  log "Health check FAILED (response: ${RESP:0:200}). Restarting vigyan.service..."
  sudo systemctl restart vigyan.service
  log "Restart attempted. Exit code: $?"
else
  log "Health check OK"
fi
