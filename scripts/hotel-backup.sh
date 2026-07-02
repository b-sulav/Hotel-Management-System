#!/usr/bin/env bash
# hotel-backup.sh — Daily archive + DB backup for the hotel system
# Place on VPS host, call from root crontab: 0 3 * * * /root/scripts/hotel-backup.sh
set -euo pipefail

PROJECT_DIR="/root/Hotel-Management-System"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/var/log/hotel-backup.log"
cd "$PROJECT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*" | tee -a "$LOG_FILE"
}

log "=== Starting daily backup + archive ==="

# Read admin token
TOKEN=""
if [ -f "$SCRIPT_DIR/../secrets/admin_token.txt" ]; then
    TOKEN="$(cat "$SCRIPT_DIR/../secrets/admin_token.txt")"
elif [ -f "secrets/admin_token.txt" ]; then
    TOKEN="$(cat secrets/admin_token.txt)"
fi

# 1) Trigger backend archive endpoint
if [ -n "$TOKEN" ]; then
    ARCHIVE_RESP=$(curl -s -X POST http://127.0.0.1:3000/api/admin/archive-old \
        -H "X-Admin-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"days":90}' \
        --max-time 30 || true)
    log "Archive API response: $ARCHIVE_RESP"
else
    log "WARNING: admin_token not found; skipping API archive."
fi

# 2) mysqldump backup
BACKUP_DIR="$PROJECT_DIR/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

DB_USER="resort_app"
if [ -f secrets/db_app_password.txt ]; then
    DB_PASS="$(cat secrets/db_app_password.txt)"
else
    log "ERROR: db_app_password.txt missing"
    exit 1
fi

DB_NAME="resort_db"

docker compose exec -T db \
    mysqldump -u "$DB_USER" -p"$DB_PASS" \
    --single-transaction --quick --routines --triggers \
    "$DB_NAME" > "$BACKUP_FILE" 2>>"$LOG_FILE"

if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"
else
    log "ERROR: Backup file not created."
    exit 1
fi

# 3) Retain only last 14 backups
KEEP=14
COUNT=$(ls -1 "$BACKUP_DIR"/backup_*.sql 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
    ls -1t "$BACKUP_DIR"/backup_*.sql | tail -n +$((KEEP+1)) | while IFS= read -r OLD; do
        log "Removing old backup: $OLD"
        rm -f "$OLD"
    done
fi

# 4) Prune very old archive records (optional safety)
if [ -n "$TOKEN" ]; then
    curl -s -X POST http://127.0.0.1:3000/api/admin/archive-old \
        -H "X-Admin-Token: $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"days":90}' \
        --max-time 30 || true
fi

log "=== Daily backup + archive complete ==="
