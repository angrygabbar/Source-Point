# Institute Management System integration

The Institute Management System is served inside SourcePoint at `/institute/`. Its API is routed through `/institute-api/`, so users stay on the SourcePoint host. SourcePoint administrators, developers, teachers and students must have an active, approved SourcePoint account to enter the module.

## Separate database and services

The module runs from its own production Compose project (`sourcepoint-institute`). It has a dedicated PostgreSQL service and persistent `postgres_data` volume, plus its own Redis, object storage and encrypted backup service. It does not connect to SourcePoint's `db` service or SourcePoint database URL. The module's PostgreSQL, Redis and storage services stay on its private internal network. Only the institute API and frontend join the shared `sourcepoint_modules` network so SourcePoint's Flask gateway can reach them; the module services publish no host ports.

## Sign-in

The SourcePoint gateway exchanges a short-lived signed identity token with the institute API. The module signs the user into an active institute account with the same email address as their SourcePoint account. Create or invite teacher and student accounts in the Institute Management System with matching email addresses. Users can choose the module's own login form from the sign-in page when needed. Each system retains its own user records and credentials.

The shared `INSTITUTE_SSO_SECRET` in SourcePoint's `.env` must match `SOURCEPOINT_SSO_SECRET` in `Institute Management System/.env`. The Mac mini deployment workflow creates and preserves these values. Do not copy the local Institute `.env` to the server.

## First institute administrator

After the services are running, create the institute and first administrator once:

```bash
cd "/Users/gaurav/Developer/Source-Point/Institute Management System"
docker compose -p sourcepoint-institute -f docker-compose.prod.yml --env-file .env run --rm backend \
  python -m app.cli create-institute \
  --name "SourcePoint Institute" \
  --code SOURCEPOINT \
  --admin-email admin@example.com \
  --admin-name "Institute Administrator"
```

Use the SourcePoint administrator's email for `--admin-email` to enable SourcePoint single sign-on. The CLI prints a temporary password once. On first sign-in, the account must choose a new Institute password; that forced change does not ask for the temporary password again. Normal password changes still require the current Institute password. This command is a one-time setup for an empty institute database.

## Teaching module removal

The legacy Teaching web blueprint is no longer registered, and the SourcePoint menu, admin dashboard and teacher/student redirects now open Institute Management System. Legacy teaching tables and mobile API routes are retained so existing teaching records and the separate mobile client are not deleted by this web replacement.
