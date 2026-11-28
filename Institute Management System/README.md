# Institute Management System

Enterprise coaching-institute and education-management ERP with four role-based portals
(administrator, teacher, student, parent) over one shared, audited backend.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript (strict), Tailwind CSS, Radix UI primitives, Lucide, TanStack Query, React Hook Form + Zod, Recharts, FullCalendar, PWA |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, Celery |
| Data | PostgreSQL 16, Redis 7, PGSTY SILO (MinIO-compatible S3 storage) |
| Edge | SourcePoint Flask gateway in the integrated deployment; Nginx for standalone development |

## Repository layout

```text
backend/            FastAPI app (app/), Alembic migrations (migrations/), Dockerfile
  app/api/v1/       Workflow routers (auth, people, classes, learning, exams, admissions, finance, …)
  app/crud/         Generic permission-aware CRUD engine + resource registry
  app/models/       SQLAlchemy models (140 tables)
  app/services/     Domain services (finance, scheduling, notifications, storage, PDF, exports, imports)
  app/integrations/ Provider adapters (SMTP, MSG91/Twilio, WhatsApp Cloud, Web Push, Razorpay, OpenAI-compatible, Zoom, Google Meet)
  app/workers/      Celery app, beat schedule and tasks
frontend/           Next.js app (src/app routes, components, features, hooks, lib)
infrastructure/     nginx config, backup/restore scripts and backup image
docs/               Architecture, schema, API, deployment, configuration, user, security, integrations, handover
docker-compose.yml        Development stack (live reload)
docker-compose.prod.yml   Production stack (+ scheduled encrypted backups)
```

## Quick start (development)

```bash
cp .env.example .env          # only if .env is missing; replace the change-me values
docker compose up --build     # first run builds images and applies migrations
# create the first institute + administrator (prints a one-time password)
docker compose exec backend python -m app.cli create-institute \
  --name "My Coaching Institute" --code MYINST --admin-email admin@example.com --admin-name "Institute Admin"
```

Open `http://localhost:8080` (or the `HTTP_PORT` you configured) and sign in. You will be asked to
change the temporary password. API docs: `http://localhost:8080/api/docs`.

The local `.env` for this workspace has already been created with fresh secrets. Keep it private;
it is excluded from the project files and should not be committed.

## Production

This project is integrated into SourcePoint at `/institute/`. Follow the [SourcePoint integration guide](../../docs/institute-management-integration.md) for the shared network, isolated PostgreSQL deployment, SourcePoint sign-in and first institute setup. The production Compose stack publishes no ports and uses its own database and persistent volume.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) · [Database schema](docs/DATABASE_SCHEMA.md) · [API](docs/API_DOCUMENTATION.md)
- [Deployment](docs/DEPLOYMENT_GUIDE.md) · [Configuration](docs/CONFIGURATION_GUIDE.md) · [Backup & restore](docs/BACKUP_RESTORE_GUIDE.md)
- [Security](docs/SECURITY_GUIDE.md) · [Integrations](docs/INTEGRATIONS_GUIDE.md) · [User guide](docs/USER_GUIDE.md)
- [Assumptions](docs/ASSUMPTIONS.md) · [Handover](docs/IMPLEMENTATION_HANDOVER.md) · [Status](IMPLEMENTATION_STATUS.md)
