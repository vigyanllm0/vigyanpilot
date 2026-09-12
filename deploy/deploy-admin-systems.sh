#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# EC2 Deploy Script — Admin Management Systems
# Run on EC2: bash deploy/deploy-admin-systems.sh
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
err() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; exit 1; }

# ─── Pre-flight checks ───
log "Pre-flight checks..."
command -v docker >/dev/null || err "Docker not installed"
command -v docker-compose >/dev/null || docker compose version >/dev/null 2>&1 || err "Docker Compose not installed"
command -v python3 >/dev/null || err "Python3 not installed"
[ -f .env ] || err ".env file not found"

# ─── Step 1: Pull latest code ───
log "Step 1: Pulling latest code..."
git fetch origin
git status
echo ""
read -p "Pull latest from origin/main? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git reset --hard origin/main
    log "Code updated to latest"
else
    warn "Skipping git pull — using current code"
fi

# ─── Step 2: Install Python dependencies ───
log "Step 2: Installing Python dependencies..."
if [ -d venv ]; then
    source venv/bin/activate
    log "Activated venv"
else
    warn "No venv found — creating one"
    python3 -m venv venv
    source venv/bin/activate
fi
pip install -q prometheus_client requests 2>&1 | tail -3
pip install -q -r requirements.txt 2>&1 | tail -3
log "Dependencies installed"

# ─── Step 3: Run database migration ───
log "Step 3: Running database migration (dry-run first)..."
python deploy/migrations/migrate.py --dry-run 2>&1 | tail -10
echo ""
read -p "Apply migration? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python deploy/migrations/migrate.py
    log "Migration applied"
else
    warn "Skipping migration"
fi

# ─── Step 4: Deploy monitoring stack ───
log "Step 4: Deploying monitoring stack..."
if [ -d deploy/monitoring ]; then
    # Set Grafana password if not set
    if ! grep -q "GRAFANA_ADMIN_PASSWORD" .env 2>/dev/null; then
        echo "GRAFANA_ADMIN_PASSWORD=vigyan-$(openssl rand -hex 8)" >> .env
        warn "Generated GRAFANA_ADMIN_PASSWORD — saved to .env"
    fi
    
    cd deploy/monitoring
    docker compose up -d 2>&1 | tail -10
    cd ../..
    
    # Wait for Grafana
    log "Waiting for Grafana to start..."
    for i in {1..30}; do
        if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
            log "Grafana is up at http://localhost:3000"
            break
        fi
        sleep 2
    done
    
    # Import dashboards
    log "Importing Grafana dashboards..."
    GRAFANA_PASS=$(grep GRAFANA_ADMIN_PASSWORD .env | cut -d= -f2)
    for dash in http-metrics business-metrics infrastructure; do
        curl -sf -X POST http://localhost:3000/api/dashboards/db \
            -u "admin:${GRAFANA_PASS}" \
            -H "Content-Type: application/json" \
            -d "{\"dashboard\": $(cat deploy/monitoring/grafana/dashboards/${dash}.json), \"overwrite\": true}" \
            >/dev/null 2>&1 && log "  Imported: ${dash}" || warn "  Failed to import: ${dash}"
    done
    
    log "Monitoring stack deployed"
else
    warn "deploy/monitoring/ not found — skipping monitoring"
fi

# ─── Step 5: Setup log rotation ───
log "Step 5: Setting up log rotation..."
if [ -f deploy/logrotate.conf ]; then
    sudo cp deploy/logrotate.conf /etc/logrotate.d/vigyanllm 2>/dev/null || warn "Could not install logrotate config"
    log "Log rotation configured"
fi

# ─── Step 6: Restart application ───
log "Step 6: Restarting application..."
if systemctl is-active --quiet vigyan; then
    sudo systemctl restart vigyan
    sleep 3
    if systemctl is-active --quiet vigyan; then
        log "Application restarted successfully"
    else
        err "Application failed to start — check: sudo journalctl -u vigyan -n 50"
    fi
else
    warn "vigyan service not found — you may need to start manually"
fi

# ─── Step 7: Health check ───
log "Step 7: Running health check..."
for i in {1..5}; do
    HEALTH=$(curl -sf http://localhost:11436/health 2>/dev/null || echo "FAIL")
    if echo "$HEALTH" | grep -q "ok"; then
        log "Health check: OK"
        break
    elif [ "$i" -eq 5 ]; then
        err "Health check failed after 5 attempts"
    fi
    sleep 3
done

# ─── Step 8: Verify Prometheus is scraping ───
log "Step 8: Verifying Prometheus..."
if curl -sf http://localhost:9090/api/v1/targets 2>/dev/null | grep -q "vigyanllm-app"; then
    log "Prometheus is scraping app metrics"
else
    warn "Prometheus may not be scraping yet — check http://localhost:9090/targets"
fi

# ─── Summary ───
echo ""
echo "═══════════════════════════════════════════════════════════"
log "DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Application:  http://localhost:11436/health"
echo "  Grafana:      http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_EC2_IP'):3000"
echo "  Prometheus:   http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_EC2_IP'):9090"
echo "  Loki:         http://localhost:3100/ready"
echo ""
echo "  Grafana login: admin / $(grep GRAFANA_ADMIN_PASSWORD .env | cut -d= -f2)"
echo ""
echo "  Dashboards: HTTP Metrics | Business Metrics | Infrastructure"
echo "  Alerts: 9 rules configured (service down, error rate, latency, disk, memory, DB, login, payment, cert)"
echo ""
echo "  To view logs: docker logs -f promtail"
echo "  To stop monitoring: cd deploy/monitoring && docker compose down"
echo "═══════════════════════════════════════════════════════════"
