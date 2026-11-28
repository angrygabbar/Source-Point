# Security guide

## Authentication

- Passwords hashed with **Argon2id** (`argon2-cffi`). Minimum length and complexity enforced on set/reset.
- Access token: JWT (HS256, `SECRET_KEY`), 15 minutes, kept **in memory only** in the browser.
- Refresh token: random opaque token (stored hashed), httpOnly + SameSite=Strict cookie `cf_refresh`
  scoped to `/api/v1/auth`, `Secure` in production, **rotated** on every refresh. Reuse of a rotated
  token (outside a 20 s concurrency grace) revokes the whole token family.
- CSRF: refresh/logout require the double-submit header `X-CSRF-Token` matching the `cf_csrf` cookie.
  All other API calls use the bearer header (not cookies) and are therefore not CSRF-exposed.
- Account lockout after `LOGIN_MAX_FAILURES` failures for `LOGIN_LOCK_MINUTES`; login rate limit
  per IP+email (Redis, in-process fallback) and an nginx rate-limit zone on `/api/v1/auth/`.
- Login history (IP, user agent, success/failure) and active session list with per-session revoke,
  "log out everywhere", admin unlock/revoke.
- Password reset: single-use, hashed, 60-minute tokens; responses do not reveal whether an account exists.
- Temporary passwords force a change at first login.

## Authorisation

- RBAC with `<module>.<action>` permissions and `_own` variants; sensitive actions use dedicated
  permissions (see CONFIGURATION_GUIDE.md).
- Every query is scoped server-side by `institute_id` from the principal (never from the request
  body), plus branch scope and ownership filters (teacher → assigned batches/sessions; student →
  self; parent → linked children only).
- Foreign keys supplied by clients are verified to belong to the same institute before writes.
- Feature flags are enforced in the API as well as the UI.
- Sensitive fields (internal remarks, counselling notes, teacher contact, salary data, answer keys)
  are masked unless the caller holds the specific permission. Answer keys are never sent to students
  before results are published.
- API keys: 256-bit random secrets stored only as SHA-256 hashes (prefix kept for identification),
  scoped to permissions, revocable, last-used tracking.

## Data protection

- Integration credentials encrypted at rest (Fernet, `ENCRYPTION_KEY`); write-only in the UI.
- Files in private MinIO bucket; downloads only via short-lived **signed links** issued after a
  permission check (`/api/v1/files/<token>`), with `Content-Disposition: attachment` for everything
  except images/video; every download is logged.
- Uploads: size limit, extension allow-list + block-list, magic-byte sniffing for known types,
  randomised object keys, original filename stored separately and sanitised.
- Financial records are append-only (DB triggers); corrections use credit notes, reversals,
  refunds and supplementary invoices. Audit log is immutable at DB level.
- Audit log records actor, IP, user agent, request id, old/new values for create/update/delete and
  all sensitive workflow actions; secrets/passwords are redacted from logs.
- Backups encrypted with AES-256 (passphrase outside the server).
- Privacy: users can download their data (`/auth/my-data`) and request account closure; retention
  settings purge old notifications/login history; financial/academic records are retained.

## Transport and headers

- TLS must be terminated in front of nginx; set `COOKIE_SECURE=true` and HTTPS `PUBLIC_BASE_URL`.
- Backend headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Cache-Control: no-store` on API responses, restrictive CSP on API responses,
  HSTS when `APP_ENV=production`.
- Frontend CSP (next.config.mjs) restricts scripts to self (+ Razorpay checkout), disallows
  framing by other origins.
- Only nginx is exposed; Postgres, Redis and MinIO are on an internal network; Redis requires a password.
- Containers run as non-root users.

## Outbound calls

- Webhook deliveries refuse private, loopback, link-local and reserved IP targets (DNS resolved at send time).
- Provider calls use timeouts and never log secrets.

## Operational checklist

1. Generate unique `SECRET_KEY`, `ENCRYPTION_KEY`, DB/Redis/MinIO passwords and backup passphrase.
2. Terminate TLS; enable HSTS at the edge.
3. Restrict SSH/Docker host access; keep the host patched; pin and update images regularly.
4. Copy backups off-site and run restore drills.
5. Review the audit log and login history regularly; remove leavers promptly (Users → deactivate).
6. Rotate API keys and provider credentials periodically.
7. Commission an independent penetration test before go-live — **no security testing was performed
   by the development agent.**
