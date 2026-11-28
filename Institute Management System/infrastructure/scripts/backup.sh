#!/usr/bin/env bash
# Coordinated, encrypted backup of PostgreSQL + object storage (MinIO/S3).
# Output: $BACKUP_DIR/classflow-<UTC timestamp>/{db.dump.enc, objects.tar.gz.enc, manifest.json}
set -euo pipefail

: "${POSTGRES_HOST:?}" "${POSTGRES_DB:?}" "${POSTGRES_USER:?}" "${PGPASSWORD:?}"
: "${S3_ENDPOINT:?}" "${S3_ACCESS_KEY:?}" "${S3_SECRET_KEY:?}" "${S3_BUCKET:?}"
: "${BACKUP_ENCRYPTION_PASSPHRASE:?BACKUP_ENCRYPTION_PASSPHRASE must be set}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION="${BACKUP_RETENTION_DAYS:-14}"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_DIR}/classflow-${TS}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

log() { echo "[backup $(date -Iseconds)] $*"; }
fail() { log "ERROR: $*"; mkdir -p "$DEST"; echo "$*" > "${DEST}/FAILED"; exit 1; }
encrypt() { openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_PASSPHRASE -in "$1" -out "$2"; }

mkdir -p "$DEST"
log "starting backup ${TS}"

# 1. Database (custom format, compressed). Taken first so object storage is a superset of referenced keys.
pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -Z 6 --no-owner -f "${WORK}/db.dump" || fail "pg_dump failed"
DB_SHA="$(sha256sum "${WORK}/db.dump" | cut -d' ' -f1)"

# 2. Object storage. Document versions use unique keys, so mirroring preserves full version history.
export MC_CONFIG_DIR="${WORK}/.mc"
mc alias set cf "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null || fail "cannot reach object storage"
mkdir -p "${WORK}/objects"
mc mirror --quiet --preserve "cf/${S3_BUCKET}" "${WORK}/objects" || fail "object mirror failed"
OBJ_COUNT="$(find "${WORK}/objects" -type f | wc -l | tr -d ' ')"
tar -C "${WORK}" -czf "${WORK}/objects.tar.gz" objects || fail "object archive failed"
OBJ_SHA="$(sha256sum "${WORK}/objects.tar.gz" | cut -d' ' -f1)"

# 3. Encrypt and write manifest.
encrypt "${WORK}/db.dump" "${DEST}/db.dump.enc" || fail "encryption failed (db)"
encrypt "${WORK}/objects.tar.gz" "${DEST}/objects.tar.gz.enc" || fail "encryption failed (objects)"
PG_VERSION="$(pg_dump --version | awk '{print $3}')"
cat > "${DEST}/manifest.json" <<EOF
{
  "created_at": "${TS}",
  "database": {"name": "${POSTGRES_DB}", "file": "db.dump.enc", "sha256_plain": "${DB_SHA}", "pg_dump_version": "${PG_VERSION}"},
  "objects": {"bucket": "${S3_BUCKET}", "file": "objects.tar.gz.enc", "sha256_plain": "${OBJ_SHA}", "object_count": ${OBJ_COUNT}},
  "encryption": "openssl aes-256-cbc pbkdf2 iter=200000",
  "verified_restore": false
}
EOF
log "backup written to ${DEST} (objects: ${OBJ_COUNT})"

# 4. Retention.
find "$BACKUP_DIR" -maxdepth 1 -type d -name 'classflow-*' -mtime +"$RETENTION" -print -exec rm -rf {} + || log "retention cleanup warning"
log "done"
