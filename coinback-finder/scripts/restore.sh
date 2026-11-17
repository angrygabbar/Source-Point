#!/usr/bin/env bash
# Restore a CoinBack schema backup into the running SourcePoint database.
# Usage: ./coinback-finder/scripts/restore.sh coinback-finder/backups/coinback-YYYYmmdd-HHMMSS.sql.gz
set -euo pipefail

MODULE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
cd "$REPO_ROOT"
FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Usage: $0 <backup.sql.gz>" >&2
  exit 1
fi

COMPOSE=(docker compose --project-directory "$REPO_ROOT" -f "$REPO_ROOT/docker-compose.yml")
echo "This replaces the CoinBack schema in SourcePoint's database with the contents of $FILE."
read -r -p "Type RESTORE to continue: " CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo "Aborted."; exit 1; }

echo "Stopping CoinBack services..."
"${COMPOSE[@]}" stop coinback-scanner coinback-api coinback-frontend

gunzip -c "$FILE" | "${COMPOSE[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U dev_user -d sourcepoint_dev_db

echo "Applying any newer migrations and restarting..."
"${COMPOSE[@]}" run --rm coinback-migrate
"${COMPOSE[@]}" up -d coinback-api coinback-scanner coinback-frontend
echo "Restore complete."
