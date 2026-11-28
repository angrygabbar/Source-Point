# Deployment guide

The production Compose stack is integrated with SourcePoint. It publishes no independent port and
runs no public nginx. SourcePoint routes `/institute/` to the Next.js frontend and `/institute-api/`
to FastAPI. See the [SourcePoint integration guide](../../docs/institute-management-integration.md).

## Prerequisites

- The SourcePoint Mac mini host with Docker/OrbStack and the Docker Compose v2 plugin.
- The SourcePoint stack running with its `sourcepoint_modules` Docker network.
- 2 vCPU / 4 GB RAM minimum for a single institute; 4 vCPU / 8 GB recommended.
- Outbound internet during image builds (PyPI, npm and container registries).

## Configure

The Mac mini deployment workflow creates the production `.env` with fresh secrets and preserves
it between deployments. The module `.env` must not be copied from a development machine. The
`INSTITUTE_SSO_SECRET` in SourcePoint's `.env` must match `SOURCEPOINT_SSO_SECRET` in the module
`.env`. The workflow maintains this pairing.

Set `PUBLIC_BASE_URL` to `https://<SourcePoint-host>/institute` for reset links, emails and payment
callbacks. Set `COOKIE_SECURE=true` in production. Keep `ENCRYPTION_KEY` and
`BACKUP_ENCRYPTION_PASSPHRASE` outside source control and never rotate them without planning for
existing encrypted data and backups.

## Build and start

Run from the Institute Management System directory after SourcePoint has created the shared network:

```bash
docker compose -p sourcepoint-institute -f docker-compose.prod.yml --env-file .env up -d --build
docker compose -p sourcepoint-institute -f docker-compose.prod.yml ps
```

Start-up order: the dedicated PostgreSQL, Redis and object storage services become healthy;
`migrate` applies Alembic migrations and seeds permissions/system roles; then the backend, worker and
frontend start. The encrypted backup service runs its daily schedule. The database, Redis and object
storage use the module's private internal network. Only the API and frontend attach to the shared
SourcePoint gateway network.

## Create the first institute

Create an institute once in the new database:

```bash
docker compose -p sourcepoint-institute -f docker-compose.prod.yml --env-file .env run --rm backend \
  python -m app.cli create-institute \
  --name "SourcePoint Institute" --code SOURCEPOINT \
  --admin-email admin@example.com --admin-name "Institute Administrator"
```

Use the SourcePoint administrator's email to enable SourcePoint sign-in. The CLI prints a temporary
password once. Change it after the first sign-in. This command is a one-time operation against an
empty institute database.

## TLS, health and monitoring

SourcePoint's existing front door terminates TLS. `PUBLIC_BASE_URL` must include `/institute`. The
module's refresh cookie is scoped to `/institute-api/api/v1/auth` so it is only sent to the module
API. HSTS is sent by the backend in production.

| Endpoint | Purpose |
|---|---|
| `GET /health` | backend liveness |
| `GET /ready` | readiness: database, Redis and object storage reachable |

Logs are JSON on stdout (`docker compose -p sourcepoint-institute -f docker-compose.prod.yml logs -f backend worker`), each request has an ID, and container logs rotate at 20 MB × 5 files.

## Upgrades

The SourcePoint Mac mini workflow builds the module, applies migrations and starts its services.
For manual upgrades, back up first and then run:

```bash
infrastructure/scripts/backup-now.sh
docker compose -p sourcepoint-institute -f docker-compose.prod.yml --env-file .env up -d --build
```

## Development stack

The standalone development stack remains available:

```bash
cp .env.example .env
docker compose up --build              # http://localhost:8080
docker compose exec backend python -m app.cli create-institute --name "Dev Institute" --code DEV --admin-email admin@dev.local --admin-name Admin
```

Backend and frontend reload on code changes. The S3 console is at `http://127.0.0.1:9001` (local
only). Development uses RustFS for S3; production uses PGSTY SILO.
