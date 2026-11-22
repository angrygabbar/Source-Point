#!/usr/bin/env bash
set -Eeuo pipefail

dump_dir="/stockai-dump"
dump_file="${STOCK_AI_DB_DUMP_FILE:-}"

if [[ -n "$dump_file" ]]; then
    dump_path="$dump_dir/$dump_file"
    if [[ ! -f "$dump_path" ]]; then
        echo "Stock AI dump file was configured but not found: $dump_path" >&2
        exit 1
    fi
else
    mapfile -d '' -t dump_files < <(
        find "$dump_dir" -maxdepth 3 -type f \
            \( -iname '*.sql' -o -iname '*.sql.gz' -o -iname '*.dump' -o -iname '*.backup' -o -iname '*.tar' \) \
            -print0 | sort -z
    )

    if (( ${#dump_files[@]} == 0 )); then
        echo "No Stock AI database dump found in $dump_dir; initializing an empty database."
        exit 0
    fi

    if (( ${#dump_files[@]} > 1 )); then
        echo "More than one Stock AI dump was found. Set STOCK_AI_DB_DUMP_FILE to the dump filename to restore." >&2
        printf '  %s\n' "${dump_files[@]}" >&2
        exit 1
    fi

    dump_path="${dump_files[0]}"
fi

echo "Restoring Stock AI database from $(basename "$dump_path") into $POSTGRES_DB."
case "${dump_path,,}" in
    *.sql)
        psql --set ON_ERROR_STOP=1 --single-transaction --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" < "$dump_path"
        ;;
    *.sql.gz)
        gunzip -c "$dump_path" | psql --set ON_ERROR_STOP=1 --single-transaction --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"
        ;;
    *.dump|*.backup|*.tar)
        pg_restore --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" "$dump_path"
        ;;
    *)
        echo "Unsupported Stock AI database dump format: $dump_path" >&2
        exit 1
        ;;
esac
