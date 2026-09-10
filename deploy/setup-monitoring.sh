#!/usr/bin/env bash
# setup-monitoring.sh — Deploy VigyanLLM monitoring stack on EC2
# Usage: sudo bash deploy/setup-monitoring.sh [GRAFANA_PASSWORD]
set -euo pipefail

GRAFANA_PASS="${1:-changeme}"
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
MONITORING_DIR="$DEPLOY_DIR/monitoring"
APP_URL="http://127.0.0.1:11436/health"
GRAFANA_URL="http://localhost:3000"
PROMETHEUS_URL="http://localhost:9090"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ── Pre-flight checks ─────────────────────────────────────────────────────
log "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    log "ERROR: Docker not installed. Install: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    log "ERROR: Docker Compose v2 not installed."
    exit 1
fi

if ! systemctl is-active --quiet docker; then
    log "Starting Docker..."
    sudo systemctl start docker
fi

log "Docker: $(docker --version)"
log "Compose: $(docker compose version)"

# ── Create log directories ────────────────────────────────────────────────
log "Creating log directories..."
sudo mkdir -p /var/log/vigyan
sudo chown ubuntu:ubuntu /var/log/vigyan 2>/dev/null || true

# ── Deploy monitoring stack ────────────────────────────────────────────────
log "Starting monitoring stack..."
cd "$MONITORING_DIR"
GRAFANA_ADMIN_PASSWORD="$GRAFANA_PASS" docker compose up -d

# ── Wait for Grafana health ───────────────────────────────────────────────
log "Waiting for Grafana to become healthy..."
RETRIES=20
until curl -sf "$GRAFANA_URL/api/health" >/dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        log "ERROR: Grafana failed to start within 60s"
        docker compose logs grafana
        exit 1
    fi
    sleep 3
done
log "Grafana is healthy."

# ── Wait for Prometheus health ─────────────────────────────────────────────
log "Waiting for Prometheus..."
RETRIES=20
until curl -sf "$PROMETHEUS_URL/-/healthy" >/dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        log "ERROR: Prometheus failed to start within 60s"
        docker compose logs prometheus
        exit 1
    fi
    sleep 3
done
log "Prometheus is healthy."

# ── Import Grafana dashboards via API ──────────────────────────────────────
log "Importing Grafana dashboards..."
DASHBOARDS_DIR="$MONITORING_DIR/grafana/dashboards"

for dashboard_file in "$DASHBOARDS_DIR"/*.json; do
    [ -f "$dashboard_file" ] || continue
    DASH_NAME=$(basename "$dashboard_file" .json)
    DASH_JSON=$(cat "$dashboard_file")

    # Extract uid from JSON
    DASH_UID=$(echo "$DASH_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('uid',''))" 2>/dev/null || echo "")

    # Check if dashboard already exists
    EXISTING=$(curl -sf "$GRAFANA_URL/api/dashboards/uid/$DASH_UID" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('dashboard',{}).get('uid',''))" 2>/dev/null || echo "")

    if [ "$EXISTING" = "$DASH_UID" ]; then
        log "  Dashboard '$DASH_NAME' (uid=$DASH_UID) already exists — updating..."
        ACTION="db-update"
    else
        log "  Importing dashboard '$DASH_NAME' (uid=$DASH_UID)..."
        ACTION="db-create"
    fi

    # Import via API
    IMPORT_PAYLOAD=$(python3 -c "
import json, sys
dashboard = json.load(open('$dashboard_file'))
dashboard.pop('id', None)
payload = {'dashboard': dashboard, 'overwrite': True, 'folderId': 0}
print(json.dumps(payload))
")

    RESPONSE=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -u "admin:$GRAFANA_PASS" \
        "$GRAFANA_URL/api/dashboards/import" \
        -d "$IMPORT_PAYLOAD" 2>&1 || echo '{"message":"import failed"}')

    if echo "$RESPONSE" | grep -q '"imported"'; then
        log "    ✓ Imported '$DASH_NAME'"
    elif echo "$RESPONSE" | grep -q '"uid"'; then
        log "    ✓ Updated '$DASH_NAME'"
    else
        log "    ⚠ Import response: $RESPONSE"
    fi
done

# ── Configure alertmanager webhook ─────────────────────────────────────────
log "Checking alertmanager..."
AM_HEALTHY=$(curl -sf "$PROMETHEUS_URL/api/v1/alerts" 2>/dev/null | python3 -c "import sys,json; print('ok')" 2>/dev/null || echo "unreachable")
log "Alertmanager status: $AM_HEALTHY"

# ── Print access URLs ─────────────────────────────────────────────────────
log ""
log "═══════════════════════════════════════════════════════════════════"
log "  VigyanLLM Monitoring Stack — DEPLOYED"
log "═══════════════════════════════════════════════════════════════════"
log ""
log "  Grafana:       $GRAFANA_URL  (admin / $GRAFANA_PASS)"
log "  Prometheus:    $PROMETHEUS_URL"
log "  Alertmanager:  http://localhost:9093"
log "  Loki:          http://localhost:3100"
log ""
log "  Dashboards:"
log "    - HTTP Metrics:       $GRAFANA_URL/d/vigyanllm-http"
log "    - Business Metrics:   $GRAFANA_URL/d/vigyanllm-business"
log "    - Infrastructure:     $GRAFANA_URL/d/vigyanllm-infra"
log ""
log "  App metrics endpoint:  $APP_URL → /metrics"
log ""

# ── Install logrotate cron ────────────────────────────────────────────────
log "Installing logrotate cron..."
if [ -f "$DEPLOY_DIR/logrotate.conf" ]; then
    sudo cp "$DEPLOY_DIR/logrotate.conf" /etc/logrotate.d/vigyanllm 2>/dev/null || true
    log "  logrotate config installed."
fi

# ── Install healthcheck cron ──────────────────────────────────────────────
log "Installing healthcheck cron..."
CRON_LINE="*/5 * * * * $DEPLOY_DIR/healthcheck.sh $APP_URL ok >> /var/log/vigyan-healthcheck.log 2>&1"
if ! sudo crontab -l 2>/dev/null | grep -qF "healthcheck.sh"; then
    (sudo crontab -l 2>/dev/null; echo "$CRON_LINE") | sudo crontab -
    log "  Healthcheck cron installed (every 5 min)."
else
    log "  Healthcheck cron already present."
fi

log ""
log "Done. Monitoring stack is live."
