#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# VigyanLLM — Local PostgreSQL → Azure PostgreSQL Migration Runner
# ──────────────────────────────────────────────────────────────────────────────
# Usage:
#   chmod +x deploy/run_migration.sh
#   ./deploy/run_migration.sh            # Full migration (after dry-run passes)
#   ./deploy/run_migration.sh --dry-run  # Validate only, no writes
#   ./deploy/run_migration.sh --resume-from users  # Resume after failure
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

MIGRATE_SCRIPT="$(cd "$(dirname "$0")" && pwd)/migrations/migrate_local_to_azure.py"
LOG_FILE="/tmp/vigyanpilot_migration_$(date +%Y%m%d_%H%M%S).log"

# ── Color output helpers ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

# ── Pre-flight checks ────────────────────────────────────────────────────────
preflight() {
    info "Running pre-flight checks ..."

    # 1. psycopg2 available
    python3 -c "import psycopg2" 2>/dev/null || fail "psycopg2 is not installed. Run: pip install psycopg2-binary"

    # 2. pg_dump available (recommended but not required — fallback works)
    if command -v pg_dump &>/dev/null; then
        ok "pg_dump found at $(command -v pg_dump)"
    else
        warn "pg_dump not found — schema extraction will use information_schema (less complete)"
    fi

    # 3. Env vars
    : "${LOCAL_DATABASE_URL:?Must set LOCAL_DATABASE_URL}"
    : "${DATABASE_URL:?Must set DATABASE_URL (Azure target)}"

    # 4. Connectivity
    info "Testing source connection ..."
    python3 -c "
import psycopg2
conn = psycopg2.connect('$LOCAL_DATABASE_URL', connect_timeout=5)
cur = conn.cursor()
cur.execute('SELECT version()')
print('  ' + cur.fetchone()[0][:60])
conn.close()
" && ok "Source (local PG) reachable" || fail "Cannot reach source database at LOCAL_DATABASE_URL"

    info "Testing target connection ..."
    python3 -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL', sslmode='require', connect_timeout=10)
cur = conn.cursor()
cur.execute('SELECT version()')
print('  ' + cur.fetchone()[0][:60])
conn.close()
" && ok "Target (Azure PG) reachable" || fail "Cannot reach Azure target at DATABASE_URL"

    # 5. Migration script exists
    [[ -f "$MIGRATE_SCRIPT" ]] || fail "Migration script not found at $MIGRATE_SCRIPT"
    ok "Migration script ready: $MIGRATE_SCRIPT"
}

# ── Dry run ──────────────────────────────────────────────────────────────────
do_dry_run() {
    info "Starting DRY RUN (schema extraction + row counts, no writes to Azure) ..."
    python3 "$MIGRATE_SCRIPT" --dry-run "$@" 2>&1 | tee -a "$LOG_FILE"
    local rc=${PIPESTATUS[0]}
    if [[ $rc -eq 0 ]]; then
        ok "Dry run completed. Review the output above."
        echo ""
        info "If row counts look correct, run:  ./deploy/run_migration.sh"
    else
        fail "Dry run failed (exit code $rc). Check $LOG_FILE for details."
    fi
}

# ── Live migration ──────────────────────────────────────────────────────────
do_migrate() {
    warn "=== LIVE MIGRATION — data will be written to Azure ==="
    echo ""
    read -rp "Type YES to confirm: " confirm
    if [[ "$confirm" != "YES" ]]; then
        info "Aborted."
        exit 0
    fi

    info "Starting live migration (this may take several minutes) ..."
    python3 "$MIGRATE_SCRIPT" "$@" 2>&1 | tee -a "$LOG_FILE"
    local rc=${PIPESTATUS[0]}

    if [[ $rc -eq 0 ]]; then
        echo ""
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║            MIGRATION COMPLETED SUCCESSFULLY                 ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Post-migration steps (in order):"
        echo ""
        echo "  1. UPDATE PRODUCTION .env"
        echo "     SSH into EC2:   ssh ubuntu@<your-ec2-host>"
        echo "     Edit .env:      nano ~/vigyanpilot/.env"
        echo "     Change:         DATABASE_URL to the Azure connection string"
        echo "     Add:            DB_SSL_MODE=require"
        echo ""
        echo "  2. RESTART THE APP"
        echo "     cd ~/vigyanpilot && docker-compose up -d --force-recreate app"
        echo ""
        echo "  3. VERIFY"
        echo "     Check logs:     docker-compose logs app --tail=50"
        echo "     Test login:     curl https://vigyanllm.in/api/health"
        echo "     Check users:    vigyanpilot_db should have all your data"
        echo ""
        echo "  4. ROLLBACK PLAN (keep local PG running for 7 days)"
        echo "     Revert .env DATABASE_URL to localhost:5432"
        echo "     Restart app:    docker-compose up -d --force-recreate app"
        echo ""
        echo "  5. AFTER 7 DAYS (cold backup then cleanup)"
        echo "     pg_dump local PG as cold backup:"
        echo "       PGPASSWORD=<pw> pg_dump -h localhost -U vigyanpilot_app \\"
        echo "         -d vigyanpilot_db --no-owner --no-acl \\"
        echo "         > /backups/vigyanpilot_final_$(date +%Y%m%d).sql"
        echo "     Then stop local PG if no longer needed."
    else
        fail "Migration failed (exit code $rc). Check $LOG_FILE for details."
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     VigyanLLM — Local PG → Azure PG Migration Runner        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Source:      ${LOCAL_DATABASE_URL:0:50}..."
    echo "Target:      ${DATABASE_URL:0:50}..."
    echo "Log:         $LOG_FILE"
    echo ""

    preflight
    echo ""

    if [[ "$1" == "--dry-run" ]]; then
        shift
        do_dry_run "$@"
    else
        do_migrate "$@"
    fi
}

main "$@"
