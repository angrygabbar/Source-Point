#!/usr/bin/env bash
# Reports CoinBack service state, API readiness and scanner heartbeat.
# Usage: ./coinback-finder/scripts/health-check.sh
set -uo pipefail

MODULE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$MODULE_ROOT/.." && pwd)"
COMPOSE=(docker compose --project-directory "$REPO_ROOT" -f "$REPO_ROOT/docker-compose.yml")
STATUS=0

echo "== Containers =="
"${COMPOSE[@]}" ps coinback-migrate coinback-api coinback-scanner coinback-frontend \
  --format 'table {{.Service}}\t{{.State}}\t{{.Health}}' || STATUS=1

echo
echo "== API readiness (from inside the backend container) =="
if "${COMPOSE[@]}" exec -T coinback-api python -c "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=5); print(r.read().decode()); sys.exit(0 if r.status==200 else 1)"; then
  echo "API ready"
else
  echo "API NOT ready"; STATUS=1
fi

echo
echo "== Frontend =="
if "${COMPOSE[@]}" exec -T coinback-frontend wget -qO- http://127.0.0.1:3000/coinback/ >/dev/null; then
  echo "Frontend responding internally at /coinback/"
else
  echo "Frontend NOT responding"; STATUS=1
fi

echo
echo "== Scanner heartbeat =="
"${COMPOSE[@]}" exec -T db psql -U dev_user -d sourcepoint_dev_db -At -c \
  "SELECT 'last heartbeat: ' || (value->>'alive_at') || '  next scan: ' || coalesce(value->>'next_scan_at','n/a') FROM coinback.app_settings WHERE key='scanner_schedule';" \
  || STATUS=1

exit $STATUS
