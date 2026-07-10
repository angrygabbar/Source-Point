#!/usr/bin/env bash
set -e

if [ "${RUN_SCHEMA_ENSURE:-1}" = "1" ]; then
  python scripts/ensure_schema.py
fi

if [ "$#" -eq 1 ]; then
  exec sh -c "$1"
fi

exec "$@"
