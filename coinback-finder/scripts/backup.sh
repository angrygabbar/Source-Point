#!/usr/bin/env bash
# Logical backup of the CoinBack schema inside SourcePoint's shared database.
# Usage: ./coinback-finder/scripts/backup.sh [output-directory]
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
cd "$MODULE_ROOT"
OUT_DIR="${1:-backups}"
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$OUT_DIR/coinback-$STAMP.sql.gz"

docker compose --project-directory "$REPO_ROOT" -f "$REPO_ROOT/docker-compose.yml" \
  exec -T db pg_dump -U dev_user -d sourcepoint_dev_db --schema=coinback --no-owner --no-privileges --clean --if-exists \
  | gzip -9 > "$FILE"
chmod 600 "$FILE"

# Keep the 30 most recent backups.
ls -1t "$OUT_DIR"/coinback-*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -f

echo "Backup written: $FILE ($(du -h "$FILE" | cut -f1))"
