# Implementation handover

## Testing statement

**Testing was intentionally not performed.** Per the master prompt, the development agent did not
write or execute unit, integration, end-to-end, load, security or accessibility tests, did not run
the application stack, and did not perform a restore drill. Build/configuration checks were run on
2026-11-28:

- Backend: all modules import; FastAPI generates the OpenAPI document (638 paths); all 140 tables
  compile to PostgreSQL DDL; worker, CLI and migration modules import.
- Frontend: `npm install` succeeded (Next.js 14.2.35 at implementation time) and the strict TypeScript
  type-check (`tsc --noEmit`) passed with 0 errors; `next build` compiled and generated all 30
  pages.
- Docker: development and production Compose configurations parsed successfully and all app images
  built successfully. The containers were not started and the application was not runtime-tested.
- Frontend dependency audit: `npm audit` reported 7 advisories (1 critical, 5 high, 1 moderate).
  Review and update affected dependencies before production use.

Treat the system as **untested**. A full QA cycle (functional, permission matrix, finance
reconciliation, concurrency, security/penetration, performance, accessibility, browser/device
matrix, backup/restore) is required before production use.

## What was delivered

| Area | Location |
|---|---|
| Backend API, services, models, worker | `backend/app` |
| Database migration (baseline + integrity triggers) | `backend/migrations/versions/0001_initial.py` |
| Frontend (4 portals, PWA) | `frontend/src`, `frontend/public` |
| Docker Compose (dev/prod), nginx | `docker-compose.yml`, `docker-compose.prod.yml`, `infrastructure/nginx` |
| Backup/restore | `infrastructure/scripts` |
| Documentation | `README.md`, `docs/*`, `IMPLEMENTATION_STATUS.md` |

## Getting started

1. `cp .env.example .env`, fill secrets (DEPLOYMENT_GUIDE.md §1).
2. `docker compose up --build` (dev) or `docker compose -f docker-compose.prod.yml --env-file .env up -d --build` (prod).
3. `docker compose exec backend python -m app.cli create-institute --name … --code … --admin-email … --admin-name …`
4. Sign in at `http://localhost:8080` (dev) with the printed temporary password.
5. Follow USER_GUIDE.md → *First-time setup*.

## Known limitations

1. **Untested** (see above).
2. Outbound webhook deliveries carry an empty signature header until a signing secret is set on
   the endpoint (*Set signing secret* action).
3. Teacher-attendance `datetime-local` inputs on the generic form display UTC-based values; the
   session page check-in flow uses server time and is unaffected.
4. Accounting is single-entry (student ledger, expenses, cashbook, bank register, budgets, FY
   close), not a double-entry general ledger with chart of accounts.
5. Statutory payroll deductions (PF/ESI/TDS/professional tax) and GST e-invoicing are not calculated.
6. Gateway refunds (Razorpay) are recorded in the ERP but must be executed in the gateway dashboard.
7. AI features extract text from text-based documents only (no OCR); outputs are drafts that must be
   reviewed.
8. Celery beat runs inside the single worker; do not scale workers without separating beat.
9. Baseline migration uses `metadata.create_all`; subsequent schema changes need proper Alembic
   revisions.
10. Frontend lint is not enforced during `next build` (`eslint.ignoreDuringBuilds`); run `npm run lint` in CI.
11. Recharts 2.x and ESLint 8 are end-of-life upstream; plan upgrades.
12. Some lower-traffic resources (library, inventory, assets, budgets, surveys …) use the generic
    metadata-driven list/form pages rather than bespoke screens.
13. No PostgreSQL row-level security; tenant isolation is enforced in the application layer.
14. Offline mode is limited to cached static assets and attendance drafts; other actions need connectivity.

## Recommended next steps

1. Stand up a staging environment and run a full QA cycle; add automated tests (pytest for
   services/permissions/finance, Playwright for critical flows).
2. Independent security review / penetration test.
3. Configure email first (password resets), then SMS/WhatsApp/payments as needed.
4. Set up off-site backup copying and a monthly restore drill.
5. CI pipeline: lint, type-check, build images, dependency scanning (pip-audit, npm audit), image scanning.
