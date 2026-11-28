#!/usr/bin/env bash
# Runs backup.sh once per day at BACKUP_SCHEDULE_HOUR (container local time, default UTC).
set -uo pipefail
HOUR="${BACKUP_SCHEDULE_HOUR:-2}"
echo "[scheduler] daily backup at ${HOUR}:00; retention ${BACKUP_RETENTION_DAYS:-14} days"
while true; do
  now_epoch=$(date +%s)
  target=$(date -d "today ${HOUR}:00" +%s)
  if [ "$target" -le "$now_epoch" ]; then
    target=$(date -d "tomorrow ${HOUR}:00" +%s)
  fi
  sleep $(( target - now_epoch ))
  if ! /scripts/backup.sh; then
    echo "[scheduler] backup FAILED at $(date -Iseconds)" >&2
  fi
done
