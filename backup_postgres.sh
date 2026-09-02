#!/usr/bin/env bash
# ==============================================================================
# SKY EXCHANGE - Automated Daily PostgreSQL Backup Script
# Place in /etc/cron.daily/backup_sky_exchange or run via crontab
# ==============================================================================

set -e

BACKUP_DIR="/var/backups/sky_exchange"
DB_NAME="sky_exchange"
DB_USER="sky_user"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/sky_exchange_${TIMESTAMP}.sql.gz"

# Export dump compressed
sudo -u postgres pg_dump "$DB_NAME" | gzip > "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"

# Remove backups older than RETENTION_DAYS
find "$BACKUP_DIR" -type f -name "sky_exchange_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup created successfully: $BACKUP_FILE"
