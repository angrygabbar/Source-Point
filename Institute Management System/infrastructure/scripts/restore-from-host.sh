#!/usr/bin/env bash
# Host helper: restore a backup. Stops app services, restores, restarts.
# Usage: infrastructure/scripts/restore-from-host.sh classflow-20260101T020000Z
set -euo pipefail
NAME="${1:?backup folder name, e.g. classflow-20260101T020000Z}"
cd "$(dirname "$0")/../.."
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"
$COMPOSE stop backend worker
$COMPOSE exec backup /scripts/restore.sh "/backups/${NAME}" --yes
$COMPOSE start backend worker
