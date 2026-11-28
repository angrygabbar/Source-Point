# Configuration guide

Configuration has three layers:

1. **Environment variables** (`.env`) – infrastructure, secrets, security defaults.
2. **Institute settings** (Settings → General / Feature flags / Integrations in the admin portal;
   stored in `institutes`, `application_settings`, `feature_flags`, `integration_configs`).
3. **Master data** – branches, academic years, courses, subjects, batches, classrooms, fee plans,
   grade scales, tax rates, compensation rules, notification templates, custom fields, roles.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | development | `production` enables strict secret checks and HSTS |
| `LOG_LEVEL` | INFO | DEBUG/INFO/WARNING/ERROR |
| `SECRET_KEY` | – (required) | JWT/signing key |
| `ENCRYPTION_KEY` | – (required) | Fernet key for integration credentials |
| `ACCESS_TOKEN_MINUTES` | 15 | Access token lifetime |
| `REFRESH_TOKEN_DAYS` | 14 | Refresh token lifetime (rotated on each use) |
| `COOKIE_SECURE` | false (dev) / true (prod) | Secure flag on auth cookies |
| `CORS_ORIGINS` | – | Comma-separated extra origins (not needed behind the bundled nginx) |
| `PUBLIC_BASE_URL` | http://localhost:8080 | External URL used in links and emails |
| `POSTGRES_DB/USER/PASSWORD` | – | Database |
| `REDIS_PASSWORD` | – | Redis auth |
| `MINIO_ROOT_USER/PASSWORD` | – | MinIO root credentials, also used as S3 keys |
| `S3_ENDPOINT` | http://minio:9000 | S3 endpoint |
| `S3_BUCKET` / `S3_REGION` | classflow / us-east-1 | Bucket (auto-created) |
| `MAX_UPLOAD_MB` | 25 | Per-file upload limit (nginx allows 30 MB bodies) |
| `DEFAULT_TIMEZONE` / `DEFAULT_CURRENCY` | Asia/Kolkata / INR | Defaults for new institutes |
| `BREVO_API_KEY` / `BREVO_FROM_EMAIL` / `BREVO_FROM_NAME` | – | Brevo transactional email fallback; synced from SourcePoint by deployment |
| `SMTP_*` | – | SMTP fallback email transport if not configured in the UI |
| `VAPID_PUBLIC_KEY/PRIVATE_KEY/SUBJECT` | – | Fallback Web Push keys |
| `HTTP_PORT` | 8080 dev / 80 prod | Published nginx port |
| `MINIO_CONSOLE_PORT` | 9001 | Dev only, bound to 127.0.0.1 |
| `BACKEND_WORKERS` | 3 | Prod gunicorn workers |
| `BACKUP_ENCRYPTION_PASSPHRASE` | – (prod required) | Backup encryption |
| `BACKUP_RETENTION_DAYS` | 14 | Local backup retention |
| `BACKUP_SCHEDULE_HOUR` | 2 | Daily backup hour (container time, UTC) |

Upload allow/deny lists and login lockout thresholds are defined in
`backend/app/core/config.py` (`ALLOWED_UPLOAD_EXTENSIONS`, `BLOCKED_UPLOAD_EXTENSIONS`,
`LOGIN_MAX_FAILURES`, `LOGIN_LOCK_MINUTES`, `RATE_LIMIT_LOGIN_PER_MINUTE`) and can be overridden
by environment variables of the same name.

## Institute settings (Settings page)

- **General** – name, legal name, logo, contact details, tax id, timezone, currency, locale,
  financial-year start month, invoice/receipt prefixes.
- **Application settings** (`/settings/app`, defaults in `services/app_settings.py`):
  `attendance.alert_threshold_percent` (75), `attendance.lock_on_submit` (true),
  `billing.billable_attendance_statuses` (present, late), `billing.auto_generate_invoices` (false),
  `billing.invoice_lead_days`, `communication.students_can_message_teachers`,
  `communication.parents_can_message_teachers`, `communication.students_can_message_students`
  (false), `communication.show_teacher_contact_to_parents` (false),
  `homework.reminder_hours_before_due` (24), `admissions.follow_up_reminder_minutes` (60),
  `syllabus.delay_alert_days` (7), `evaluation.pending_alert_days` (3),
  `retention.login_history_days` (365), `retention.notification_days` (180),
  `retention.audit_log_days` (0 = keep forever), `ai.monthly_request_limit` (500),
  `ai.allow_student_data` (false), `storage.quota_warning_percent` (85).
  Late-fee rules, due days and tax are configured on fee plans; invoice prefixes and the
  financial-year start month on the institute.
- **Feature flags** (`services/feature_flags.py`) – attendance, homework, materials, billing,
  teacher_compensation, examinations, lms, admissions, hr_payroll, parent_portal, library,
  inventory, multi_branch, saas, accounting, communication, email, sms, whatsapp, push,
  online_payments, ai, video_meetings. Provider-backed flags are off by default. Disabled modules
  are hidden in the UI and rejected by the API (HTTP 403 `module_disabled`).
- **Integrations** – provider credentials, encrypted at rest (see INTEGRATIONS_GUIDE.md).
- **API keys** – scoped keys for external systems; the secret is shown once.

## Roles and permissions

System roles (cannot be deleted, can be cloned): institute_admin, branch_admin,
academic_coordinator, teacher, student, parent, accountant, receptionist, librarian, hr_manager,
counsellor. Custom roles are composed from permission codes `<module>.<action>` with actions
`read`, `read_own`, `write`, `write_own`, `delete`, plus sensitive permissions (see
`core/permissions.py::SENSITIVE`): `attendance.reopen`, `attendance.correct_approve`,
`invoices.adjust`, `invoices.cancel`, `payments.reverse`, `refunds.approve`, `students.archive`,
`students.sensitive`, `grades.modify`, `results.approve`, `payroll.approve`,
`counselling.restricted`, `audit.read_all`, `tenant.admin`, `branch.admin`, `teachers.contact`,
`admissions.counselling`, `schedules.override_conflict`, `finance.close_year`, `platform.admin`.
Branch-limited users only see their assigned branches.
