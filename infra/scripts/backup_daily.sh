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
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
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

# Upload to S3 if bucket is configured
if [ -n "${S3_BUCKET}" ]; then
    echo "[$(date)] Uploading to s3://${S3_BUCKET}/db-backups/..."
    if command -v aws &>/dev/null; then
        aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/db-backups/${DB_NAME}_${TIMESTAMP}.sql.gz" \
            --only-show-errors && \
            echo "[$(date)] S3 upload complete" || \
            echo "[$(date)] WARNING: S3 upload failed"
    else
        echo "[$(date)] WARNING: AWS CLI not found, skipping S3 upload"
    fi
else
    echo "[$(date)] S3_BACKUP_BUCKET not set, skipping cloud upload"
fi

# Rotate: delete local backups older than retention period
echo "[$(date)] Cleaning local backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# List remaining local backups
echo "[$(date)] Current local backups:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "  (none)"

echo "[$(date)] Backup complete."
