# Backup and restore guide

Production compose includes a `backup` service (`infrastructure/scripts/`) that takes a
**coordinated** backup of PostgreSQL and the object-storage bucket every day at
`BACKUP_SCHEDULE_HOUR` (UTC).

## What a backup contains

```text
/backups/classflow-<UTC timestamp>/
  db.dump.enc           pg_dump custom format, AES-256-CBC (PBKDF2, 200k iterations)
  objects.tar.gz.enc    full mirror of the bucket (all document/material/submission versions)
  manifest.json         timestamp, SHA-256 of plaintext artefacts, object count, pg_dump version
  FAILED                present only if the run failed (with the reason)
```

The database is dumped first; object keys are unique and versions are never overwritten, so the
object archive is always a superset of what the dump references. Backups older than
`BACKUP_RETENTION_DAYS` are pruned.

Backups are stored in the `backup_data` Docker volume. **Copy them off the host** (e.g. a cron job
running `docker run --rm -v classflow_backup_data:/b alpine tar -C /b -cf - . | <your offsite uploader>`
or by mounting a network share at `/backups`). The volume name is prefixed by the compose project
name (`docker volume ls | grep backup_data`).

## Manual backup

```bash
infrastructure/scripts/backup-now.sh
docker compose -f docker-compose.prod.yml exec backup ls -l /backups
```

## Restore

Restoring **overwrites** the current database and objects.

```bash
# full restore (stops backend + worker, restores, starts them again)
infrastructure/scripts/restore-from-host.sh classflow-20260101T020000Z

# manual / partial
docker compose -f docker-compose.prod.yml stop backend worker
docker compose -f docker-compose.prod.yml exec backup /scripts/restore.sh /backups/classflow-20260101T020000Z --yes --db-only
docker compose -f docker-compose.prod.yml exec backup /scripts/restore.sh /backups/classflow-20260101T020000Z --yes --objects-only
docker compose -f docker-compose.prod.yml start backend worker
```

The restore script refuses to run without `--yes`, refuses backups marked `FAILED`, and verifies
SHA-256 checksums before applying anything. The database restore runs in a single transaction.

Restoring onto a new server: deploy the stack with the **same** `ENCRYPTION_KEY` (otherwise stored
integration credentials cannot be decrypted) and `BACKUP_ENCRYPTION_PASSPHRASE`, copy the backup
folder into the `backup_data` volume, then run the restore.

## Restore verification (recommended monthly)

1. Restore the latest backup into a separate staging stack.
2. Log in, open a student ledger, download a material and an invoice PDF.
3. Compare `object_count` in `manifest.json` with `mc ls --recursive` on the restored bucket.

The development agent did not execute a restore drill (testing was intentionally not performed).
