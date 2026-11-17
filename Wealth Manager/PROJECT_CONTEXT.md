# Wealth Manager Module Context

Last updated: November 17, 2026.

## Product

Wealth Manager is a SourcePoint module for monthly finance tracking, budgets, investments, loans, goals, net-worth analytics, planning, reports, and smart insights. The existing React screens and Spring Boot finance services stay in this directory. SourcePoint owns sign-in and the site entry point.

## Architecture

```text
Browser at /wealth-manager
  -> React app bundled into SourcePoint's static assets
  -> SourcePoint session-token endpoint
  -> SourcePoint /wealth-api proxy
  -> Spring Boot API
  -> SourcePoint PostgreSQL database
```

The browser does not keep a finance password or long-lived token. It obtains a five-minute HS256 token from SourcePoint using the current Flask session and refreshes it through the same endpoint. Spring verifies the signature, issuer, audience, expiry, and SourcePoint user id.

All API requests resolve to a Wealth Manager `users` profile linked by `sourcepoint_user_id` to SourcePoint's `user.id`. If a legacy Wealth Manager profile in the shared database has the same email, it is linked on first use. Finance repositories continue to scope rows to the linked profile UUID.

## Build and run

The supported local entry point is `docker compose up --build` from the SourcePoint repository root. The root Dockerfile builds `frontend/` and puts the resulting files under `static/wealth_manager`. Root Compose starts `wealth-manager-api` against the same PostgreSQL database as Flask.

For Vite development, run SourcePoint at port 5000, then run `npm ci && npm run dev` from `frontend/`. Vite proxies `/api/v1/wealth-manager/token` and `/wealth-api` to SourcePoint.

## Database

Flyway owns the finance module tables in the shared SourcePoint PostgreSQL database. New shared databases baseline at migration version 3 and run `V4__sourcepoint_module_integration.sql`, which creates the complete Wealth Manager schema without inserting the old demo rows. The migration adds `sourcepoint_user_id`, removes the Wealth Manager password hash, and makes age optional until the user fills it in.

SourcePoint's SQLAlchemy/Alembic migrations continue to own SourcePoint tables. The finance table names are separate (`users`, `monthly_finance`, `goals`, `investments`, `loans`, `reports`, `monthly_budgets`); the user foreign key points to SourcePoint's quoted `"user"` table.

## Environment

SourcePoint:

- `WEALTH_MANAGER_API_URL`: Spring API base URL, including `/api`
- `WEALTH_MANAGER_SSO_SECRET`: same random secret configured for Spring, at least 32 bytes

Spring Boot:

- `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`: SourcePoint's shared PostgreSQL database
- `WEALTH_MANAGER_SSO_SECRET`: same value as SourcePoint

Do not use the local Compose fallback secret in production. Keep the Spring API private behind SourcePoint's proxy when the deployment platform supports private service networking.

## Finance model

- `monthly_finance`: monthly income, expenses, assets, investments, liabilities, and calculated totals; one row per user and month.
- `monthly_budgets`: category limits and alert thresholds; one row per user, month, and category.
- `goals`: named savings targets with progress and estimated completion.
- `investments`: investment positions and current values.
- `loans`: balances, rates, EMI, and tenure.
- `reports`: monthly report snapshots.

The React app uses local view state in `App.tsx`; `Shell.tsx` defines the existing screens. Finance calculations and ownership checks remain in Spring services.

## Legacy data

Rows in the old standalone Wealth Manager database are not copied by the schema migration. Export and import that database into SourcePoint's database before production cutover if it contains financial records to preserve. Once imported, users with matching emails are linked to their SourcePoint account on first access.
