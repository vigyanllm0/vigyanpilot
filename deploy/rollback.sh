#!/usr/bin/env bash
# rollback.sh — Rollback VigyanLLM to a specific commit
# Usage: ./deploy/rollback.sh [COMMIT_SHA]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="vigyan"
HEALTH_URL="http://127.0.0.1:11436/health"
MAX_RETRIES=3

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cd "$REPO_DIR"

# ── Resolve target commit ─────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
    TARGET_SHA="$1"
else
    log "Recent commits:"
    git log --oneline -10
    echo ""
    read -rp "Enter commit SHA to rollback to: " TARGET_SHA
fi

# Validate commit exists
if ! git rev-parse --verify "$TARGET_SHA" &>/dev/null; then
    log "ERROR: Invalid commit SHA: $TARGET_SHA"
    exit 1
fi

CURRENT_SHA=$(git rev-parse --short HEAD)
TARGET_SHORT=$(git rev-parse --short "$TARGET_SHA")
log "Rolling back: $CURRENT_SHA → $TARGET_SHORT"

# ── Stash dirty state ─────────────────────────────────────────────────────
if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet HEAD 2>/dev/null; then
    log "Stashing uncommitted changes..."
    git stash push -m "pre-rollback-$(date +%s)"
    STASHED=true
else
    STASHED=false
fi

# ── Reset to target commit ────────────────────────────────────────────────
log "Resetting to $TARGET_SHORT..."
git reset --hard "$TARGET_SHA"
log "Now at $TARGET_SHORT"

# ── Run migrations (dry-run first) ────────────────────────────────────────
log "Running database migrations (dry-run)..."
if [ -f "deploy/migrations/migrate.py" ]; then
    DRY_RUN_OUTPUT=$(python3 deploy/migrations/migrate.py --dry-run 2>&1 || echo "DRY_RUN_FAILED")
    log "  Dry-run result: $DRY_RUN_OUTPUT"

    if echo "$DRY_RUN_OUTPUT" | grep -qi "error\|fail"; then
        log "WARNING: Dry-run reported errors. Proceeding anyway (check manually)."
    fi

    log "Running migrations for real..."
    python3 deploy/migrations/migrate.py 2>&1 || {
        log "ERROR: Migration failed. Check logs."
        log "Rolling back git reset..."
        git reset --hard "$CURRENT_SHA"
        exit 1
    }
    log "  Migrations complete."
else
    log "  No migration script found — skipping."
fi

# ── Install dependencies if needed ────────────────────────────────────────
if [ -f "requirements.txt" ]; then
    log "Installing dependencies..."
    pip install -r requirements.txt -q 2>&1 | tail -1 || true
fi

# ── Restart service ───────────────────────────────────────────────────────
log "Restarting $SERVICE_NAME service..."
if systemctl is-active --quiet "$SERVICE_NAME.service" 2>/dev/null; then
    sudo systemctl restart "$SERVICE_NAME.service"
    log "  Service restarted."
elif command -v docker &>/dev/null && docker ps --format '{{.Names}}' | grep -q "vigyan"; then
    log "  Detected Docker deployment — restarting container..."
    docker compose -f deploy/docker-compose.yml restart app 2>/dev/null || docker restart vigyan-app 2>/dev/null || true
else
    log "  WARNING: Service '$SERVICE_NAME' not found via systemctl or Docker."
    log "  You may need to restart manually."
fi

# ── Health check ──────────────────────────────────────────────────────────
log "Running health checks (max ${MAX_RETRIES} retries)..."
HEALTHY=false
for i in $(seq 1 "$MAX_RETRIES"); do
    sleep 3
    RESP=$(curl -sf --max-time 5 "$HEALTH_URL" 2>/dev/null || echo "FAIL")
    if echo "$RESP" | grep -qi "ok\|healthy\|version"; then
        HEALTHY=true
        break
    fi
    log "  Attempt $i/$MAX_RETRIES failed — retrying in 3s..."
done

# ── Print status ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════"
if [ "$HEALTHY" = true ]; then
    log "  ROLLBACK SUCCESSFUL"
    log "  Now running: $TARGET_SHORT"
    log "  Health: OK"
else
    log "  ROLLBACK COMPLETED but health check FAILED"
    log "  Service may need manual investigation."
    log "  Check: journalctl -u $SERVICE_NAME --no-pager -n 50"
fi
echo "═══════════════════════════════════════════════════════════════════"
echo ""
log "Previous commit: $CURRENT_SHA"
log "Rolled back to: $TARGET_SHORT"
log "Git log:"
git log --oneline -5
