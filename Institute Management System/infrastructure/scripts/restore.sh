#!/usr/bin/env bash
# Restore a ClassFlow backup created by backup.sh.
# Usage (inside the backup container): /scripts/restore.sh /backups/classflow-<timestamp> --yes [--db-only|--objects-only]
# Stop the backend and worker before restoring:  docker compose -f docker-compose.prod.yml stop backend worker
set -euo pipefail

SRC="${1:-}"
CONFIRM="${2:-}"
MODE="${3:-all}"
[ -n "$SRC" ] && [ -d "$SRC" ] || { echo "Usage: restore.sh <backup-dir> --yes [--db-only|--objects-only]"; exit 2; }
[ "$CONFIRM" = "--yes" ] || { echo "Refusing to restore without --yes (this OVERWRITES the current database and objects)"; exit 2; }
[ -f "$SRC/FAILED" ] && { echo "Backup is marked FAILED: $(cat "$SRC/FAILED")"; exit 1; }
: "${BACKUP_ENCRYPTION_PASSPHRASE:?}" "${POSTGRES_HOST:?}" "${POSTGRES_DB:?}" "${POSTGRES_USER:?}" "${PGPASSWORD:?}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
log() { echo "[restore $(date -Iseconds)] $*"; }
decrypt() { openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_PASSPHRASE -in "$1" -out "$2"; }
expect_sha() { grep "\"$1\":" "$SRC/manifest.json" | grep -o '"sha256_plain": "[a-f0-9]*"' | grep -o '[a-f0-9]\{64\}'; }

if [ "$MODE" != "--objects-only" ]; then
  log "decrypting database dump"
  decrypt "$SRC/db.dump.enc" "$WORK/db.dump"
  [ "$(sha256sum "$WORK/db.dump" | cut -d' ' -f1)" = "$(expect_sha database)" ] || { log "database checksum mismatch"; exit 1; }
  log "restoring database ${POSTGRES_DB} (existing objects are dropped first)"
  pg_restore -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction "$WORK/db.dump"
fi

if [ "$MODE" != "--db-only" ]; then
  : "${S3_ENDPOINT:?}" "${S3_ACCESS_KEY:?}" "${S3_SECRET_KEY:?}" "${S3_BUCKET:?}"
  log "decrypting object archive"
  decrypt "$SRC/objects.tar.gz.enc" "$WORK/objects.tar.gz"
  [ "$(sha256sum "$WORK/objects.tar.gz" | cut -d' ' -f1)" = "$(expect_sha objects)" ] || { log "objects checksum mismatch"; exit 1; }
  tar -C "$WORK" -xzf "$WORK/objects.tar.gz"
  export MC_CONFIG_DIR="$WORK/.mc"
  mc alias set cf "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null
  mc mb --ignore-existing "cf/${S3_BUCKET}" >/dev/null
  mc mirror --quiet --overwrite "$WORK/objects" "cf/${S3_BUCKET}"
fi

log "restore finished. Start services again and verify the application before resuming operations."
