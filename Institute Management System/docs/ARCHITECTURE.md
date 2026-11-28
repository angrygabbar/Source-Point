# Architecture

## Topology

```mermaid
flowchart LR
  U[Browser / PWA] -->|HTTP :HTTP_PORT| N[nginx]
  N -->|/| F[frontend: Next.js]
  N -->|/api/*, /health, /ready| B[backend: FastAPI + gunicorn]
  B --> P[(PostgreSQL)]
  B --> R[(Redis)]
  B --> M[(MinIO / S3)]
  W[worker: Celery + beat] --> P
  W --> R
  W --> M
  W -->|optional, when configured| X[Email / SMS / WhatsApp / Push / Webhooks]
  K[backup (prod)] --> P
  K --> M
```

Only nginx is published. PostgreSQL, Redis and MinIO (API and console) stay on the private Docker
network (`classflow`). In development the MinIO console is bound to `127.0.0.1` only.

## Modular monolith

The backend is one deployable FastAPI application with clear domain modules:

| Module | Code |
|---|---|
| Identity & access | `api/v1/auth.py`, `api/v1/admin.py`, `api/deps.py`, `core/permissions.py` |
| Tenancy & academics | `models/tenancy.py`, `models/identity.py`, generic resources |
| Class operations | `api/v1/classes.py`, `services/scheduling.py` |
| Learning | `api/v1/learning.py` (materials, homework, syllabus, LMS, discussions, meetings) |
| Examinations | `api/v1/exams.py` |
| Admissions CRM | `api/v1/admissions.py` |
| Finance & accounting | `api/v1/finance.py`, `api/v1/operations.py`, `services/finance.py` |
| Communication | `api/v1/communication.py`, `services/notifications.py` |
| Reports & dashboards | `api/v1/reports.py` |
| Platform | `api/v1/platform.py` (health, search, imports, jobs, AI), `api/v1/files.py` |

### Generic resource engine

`app/crud/engine.py` turns each registered SQLAlchemy model (`app/crud/resources.py`, ~110
resources) into a REST resource with list/filter/sort/paginate/search, export (CSV/XLSX/PDF),
create/update/archive/delete, per-record audit history and Pydantic schemas generated from the
model. It enforces, for every request:

- tenant isolation (`institute_id` from the authenticated principal, never from the client),
- branch scope (branch-limited roles and the branch selector header),
- role/permission checks (`<module>.read|read_own|write|write_own|delete`),
- resource-level ownership filters for teachers, students and parents (`owner`/`own_filter`),
- cross-tenant reference validation on every foreign key written,
- field masking for sensitive columns (`info={"sensitive": "<perm>"}`),
- audit logging with old/new values.

`GET /api/v1/meta/resources` exposes the field metadata so the frontend renders forms/tables
generically (`components/data/resource-form.tsx`, `resource-list.tsx`). Workflows with business
rules (attendance submission, payments, grading, payroll…) are dedicated routers.

### Transactions and events

Financial and attendance operations run in a single database transaction with row locks
(`SELECT … FOR UPDATE`). Side effects (notifications, webhooks) are written to `event_outbox` in
the same transaction and dispatched by the worker after commit (`workers/tasks.py::dispatch_outbox`),
with dedupe keys to prevent repeated notifications.

### Worker schedule (Celery beat)

| Task | Schedule |
|---|---|
| dispatch_outbox | every 15 s |
| send_deliveries (email/SMS/WhatsApp/push) | every 30 s, exponential retry |
| send_webhooks | every 60 s, SSRF-guarded, HMAC-signed |
| finalise_exam_attempts | every 60 s |
| follow_up_reminders | every 15 min |
| homework_reminders | hourly |
| generate_upcoming_sessions (21 days) | daily 00:30 |
| daily_finance (overdue, late fees, per-class charges, optional auto-invoicing, fee reminders) | daily 01:00 |
| daily_academic_alerts (attendance, syllabus delay, pending evaluation) | daily 07:00 |
| library_reminders | daily 08:00 |
| usage_and_retention | daily 03:00 |

Beat runs inside the single worker container (`--beat`). Do not scale the worker horizontally
without moving beat into its own service.

## Frontend

- `src/app/(app)/*` – authenticated routes inside the application shell (`components/layout/app-shell.tsx`).
- Access token held in memory only; refresh token is an httpOnly, SameSite=Strict cookie scoped to
  `/api/v1/auth`; refresh/logout use a double-submit CSRF header.
- Navigation is computed from the user's permissions and feature flags (`lib/nav.ts`).
- Generic list/detail pages: `/r/<resource>` and `/r/<resource>/<id>`; dedicated pages for
  dashboards, timetable, sessions/attendance, students, teachers, materials, homework, exams,
  admissions, finance, payroll, reports, settings, users, messaging, notifications, LMS.
- PWA: `public/manifest.webmanifest`, `public/sw.js` (caches static assets only, never API data),
  offline attendance drafts stored as student-id/status pairs only.
