#!/usr/bin/env bash
# Host helper: trigger an immediate backup using the production stack's backup service.
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose -f docker-compose.prod.yml --env-file .env exec backup /scripts/backup.sh
