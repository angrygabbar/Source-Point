# SourcePoint Wealth Manager Module

Wealth Manager is integrated into SourcePoint as an authenticated module. Its React screens and Spring Boot finance API remain organized as a module, while users enter through SourcePoint and use their existing SourcePoint account.

## Runtime

- SourcePoint serves the built React app at `/wealth-manager`.
- SourcePoint proxies `/wealth-api/*` to the Spring Boot API.
- The Spring Boot API and SourcePoint use the same PostgreSQL database.
- Flyway manages the Wealth Manager tables in that database. `V4__sourcepoint_module_integration.sql` creates the module schema and links finance profiles to SourcePoint's `user.id`.
- The API accepts only short-lived JWTs signed by SourcePoint. Login, registration, and password management belong to SourcePoint.

The financial modules remain scoped to a Wealth Manager profile row. A profile is linked by `sourcepoint_user_id`; existing rows with the same email are linked on the first authenticated request. New SourcePoint accounts receive a finance profile on first use.

## Local development

Run the SourcePoint stack from the repository root:

```bash
docker compose up --build
```

Open SourcePoint at `http://localhost:5000`, sign in with a SourcePoint account, then open Wealth Manager from the SourcePoint navigation. The Compose setup builds the React app into SourcePoint, starts the finance API, and points both apps at SourcePoint's PostgreSQL database.

For frontend development, run SourcePoint on port 5000 and start Vite from `frontend/`:

```bash
npm ci
npm run dev
```

Vite proxies the SourcePoint session-token and finance API paths to Flask.

## Production configuration

Configure the Spring service with the same PostgreSQL database used by SourcePoint:

- `SPRING_DATASOURCE_URL`: JDBC URL for the SourcePoint PostgreSQL database
- `SPRING_DATASOURCE_USERNAME`
- `SPRING_DATASOURCE_PASSWORD`
- `WEALTH_MANAGER_SSO_SECRET`: a random secret of at least 32 bytes

Configure SourcePoint with:

- `WEALTH_MANAGER_API_URL`: the Spring API base URL, including `/api`
- `WEALTH_MANAGER_SSO_SECRET`: the exact same secret configured for Spring

Keep the Spring API private behind SourcePoint's `/wealth-api` proxy where possible. Do not use the local Compose fallback secret in production.

## Finance features

The module retains its existing finance screens and API behavior:

- Monthly cash flow, budgets, investments, loans, and goals
- Dashboard, net-worth and cash-flow analytics, planning scenarios, and smart insights
- Monthly reports with PDF and Excel exports
- Per-user ownership checks on finance records

## Existing Wealth Manager data

The integration migration links a finance profile already present in the shared database when its email matches the authenticated SourcePoint account. Data in the former standalone Wealth Manager database is not copied automatically; export and import that database before switching production traffic if it contains records that need to be retained.
