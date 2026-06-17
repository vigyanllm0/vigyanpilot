#!/usr/bin/env bash
# =============================================================
# Daily PostgreSQL Backup Script
# Schedule via cron: 0 2 * * * /opt/vigyanpilot/infra/scripts/backup_daily.sh
# =============================================================

set -euo pipefail

BACKUP_DIR="/opt/vigyanpilot_backups"
CONTAINER="vigyanpilot_postgres"
DB_NAME="vigyanpilot_db"
DB_USER="vigyanpilot_app"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting backup..."

# Check container is running
if ! docker inspect --format='{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q true; then
    echo "ERROR: Container ${CONTAINER} is not running!"
    exit 1
fi

# Run pg_dump inside container, compress, write to host
docker exec "${CONTAINER}" \
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --verbose \
    2>/dev/null | gzip > "${BACKUP_FILE}"

# Verify backup is not empty
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file is empty!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup completed: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Rotate: delete backups older than retention period
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# List remaining backups
echo "[$(date)] Current backups:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "  (none)"

echo "[$(date)] Backup complete."
