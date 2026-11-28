# API documentation

- Base path: `/api/v1` · OpenAPI JSON: `/api/v1/openapi.json` · Swagger UI: `/api/docs` · ReDoc: `/api/redoc`
- Auth: `Authorization: Bearer <access token>` (15 min). Refresh via `POST /auth/refresh` with the
  `cf_refresh` httpOnly cookie and header `X-CSRF-Token: <cf_csrf cookie>`.
- Integration clients may use `X-API-Key: cfk_…` (scopes = permission codes).
- Optional headers: `X-Branch-Id` (branch selector), `X-Institute-Id` (platform administrators only),
  `Idempotency-Key` (required for `POST /payments`).
- Errors: `{"error": {"code", "message", "request_id", "details?"}}`; every response carries `X-Request-ID`.

## Generic resources

Every registered resource `<r>` supports (subject to permissions and feature flags):

| Method | Path | Notes |
|---|---|---|
| GET | `/<r>` | `page`, `page_size` (≤200), `sort` (`field` / `-field`, comma separated), `q` (search), any column as filter, operators `__in`, `__gte`, `__lte`, `__gt`, `__lt`, `__ne`, `__isnull`, `__ilike`, `include_archived` |
| GET | `/<r>/export?format=csv\|xlsx\|pdf` | same filters; >5 000 rows → 202 + background job |
| GET | `/<r>/{id}` | includes `display` labels for foreign keys |
| GET | `/<r>/{id}/history` | audit trail (staff) |
| POST | `/<r>` | schema generated from the model; extra fields rejected |
| PATCH | `/<r>/{id}` | partial update, optional `change_reason` |
| DELETE | `/<r>/{id}?reason=` | archives when the model supports archival, otherwise deletes if unreferenced |
| POST | `/<r>/{id}/restore` | archived records |
| GET | `/meta/resources[/<r>]` | field metadata used by the UI |

Registered resources (URL names): branches, academic-years, classrooms, holidays, courses, subjects,
batches, batch-subjects, students, teachers, parents, student-parents, counselling-records,
enrollments, enrollment-subjects, teacher-assignments, teacher-availability, schedules,
schedule-exceptions, class-sessions, class-session-teachers, student-attendance, teacher-attendance,
attendance-corrections, attendance-audit-logs, materials, material-versions, material-access,
documents, file-download-logs, assignments, assignment-targets, submissions, assignment-grades,
syllabus-chapters, syllabus-progress, lesson-plans, lms-modules, lms-lessons, lesson-progress,
course-completions, discussion-threads, online-meetings, grade-scales, examinations, questions,
exam-questions, exam-results, exam-attempts, re-evaluation-requests, campaigns, leads, enquiries,
follow-ups, demo-classes, admission-records, fee-plans, fee-plan-items, fee-agreements, invoices,
invoice-items, billable-charges, payments, payment-allocations, refunds, credit-notes,
ledger-entries, vendors, expense-categories, expenses, purchase-records, cashbook-entries,
bank-transactions, budgets, financial-years, tax-rates, compensation-rules, payroll-periods,
teacher-payables, payslips, teacher-payouts, teacher-leaves, leave-balances, employment-records,
performance-reviews, announcements, parent-meetings, surveys, survey-responses, parent-consents,
notification-templates, notification-deliveries, books, library-members, book-loans,
inventory-items, inventory-transactions, assets, asset-assignments, maintenance-records,
custom-fields, webhook-endpoints, webhook-deliveries, audit-logs, jobs, ai-requests,
tenant-subscriptions, usage-records.

## Workflow endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all`, `GET/PATCH /auth/me`, `POST /auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`, `GET /auth/login-history`, `GET /auth/my-data`, `POST /auth/request-account-closure` |
| Users & roles | `GET/POST /users`, `GET/PATCH /users/{id}`, `PUT /users/{id}/roles`, `POST /users/{id}/reset-link`, `/unlock`, `/revoke-sessions`, `GET /users/{id}/login-history`, `GET /login-history`, `GET /permissions`, `GET/POST /roles`, `PUT/DELETE /roles/{id}` |
| Institute & settings | `GET/PATCH /institutes/current`, `GET/POST /institutes/current/logo`, `GET/PUT /settings/feature-flags`, `GET/PUT /settings/app`, `GET /integrations`, `PUT /integrations/{type}/{provider}`, `GET/POST /api-keys`, `DELETE /api-keys/{id}`, `PUT /webhook-endpoints/{id}/secret` |
| Platform | `GET/POST /platform/institutes`, `PATCH /platform/institutes/{id}`, `GET/POST /platform/plans` |
| People | `GET /students/{id}/profile`, `POST /students/{id}/withdraw`, `/readmit`, `/transfer-batch`, `/transfer-branch`, `/create-login`, `/parents`, `/photo`; `GET /students/{id}/photo`, `/id-card.pdf`, `/certificate.pdf`; `POST /students/promote`; `GET /teachers/{id}/profile`, `POST /teachers/{id}/exit`, `/create-login`, `/photo`; `POST /parents/{id}/create-login`; `POST /teacher-leaves/{id}/decide`, `/cancel`; documents: `POST /documents/upload`, `POST /documents/{id}/versions`, `GET /documents/by-owner/{type}/{id}`, `GET /documents/{id}/download-link` |
| Timetable & sessions | `GET /class-sessions/calendar`, `POST /schedules/generate-sessions`, `POST /class-sessions/check-conflicts`, `POST /class-sessions`, `PATCH /class-sessions/{id}`, `GET /class-sessions/{id}/detail`, `POST /class-sessions/{id}/start`, `/complete`, `/cancel`, `/reschedule`, `/substitute`, `/remove-substitute/{teacher}`, `/teacher-absent` |
| Attendance | `GET/PUT /class-sessions/{id}/attendance`, `POST /class-sessions/{id}/attendance/reopen`, `POST /attendance/corrections`, `POST /attendance/corrections/{id}/decide`, `GET/PUT /class-sessions/{id}/teacher-attendance`, `POST /class-sessions/{id}/teacher-attendance/verify` |
| Materials | `POST /materials/upload` (multipart, multiple files), `POST /materials/{id}/versions`, `GET /materials/{id}/versions`, `GET /materials/{id}/download-link` |
| Homework | `PUT /assignments/{id}/targets`, `POST /assignments/{id}/attachments`, `/publish`, `/status`, `GET /assignments/{id}/submissions`, `/detail`, `POST /assignments/{id}/my-submission`, `POST /submissions/{id}/grade`, `/request-resubmission`, `GET /submissions/{id}`, `GET /submission-files/{id}/download-link`, `GET /assignment-attachments/{id}/download-link`, `GET/POST /assignments/{id}/comments` |
| Syllabus & LMS | `GET /syllabus/progress`, `POST /lms/lessons/{id}/progress`, `GET /lms/courses/{id}/outline`, `POST /discussions`, `GET /discussions/{id}`, `POST /discussions/{id}/posts`, `/moderate`, `POST /discussion-posts/{id}/report`, `POST /online-meetings` |
| Examinations | `POST /examinations/{id}/questions`, `DELETE /examinations/{id}/questions/{qid}`, `GET /examinations/{id}/paper`, `POST /examinations/{id}/status`, `POST /examinations/{id}/attempt/start`, `GET /examinations/{id}/attempt`, `PUT /examinations/{id}/attempt/answers`, `POST /examinations/{id}/attempt/submit`, `GET /examinations/{id}/manual-grading`, `POST /exam-responses/{id}/grade`, `GET /examinations/{id}/results`, `PUT /examinations/{id}/marks`, `POST /examinations/{id}/compute`, `/approve`, `/publish`, `POST /exam-results/{id}/re-evaluation`, `POST /re-evaluation-requests/{id}/decide`, `GET /students/{id}/marksheet.pdf`, `/report-card.pdf`, `POST /questions/{id}/approve` |
| Admissions | `POST /admissions/enquiries`, `GET /admissions/pipeline`, `POST /admissions/enquiries/{id}/stage`, `/offer`, `/convert`, `POST /admissions/follow-ups/{id}/complete`, `GET /admissions/conversion` |
| Fees & billing | `POST /invoices`, `POST /invoices/{id}/issue`, `/cancel`, `/credit-note`, `/supplementary`, `GET /invoices/{id}/detail`, `/pdf`, `POST /billing/generate-invoices`, `/billing/per-class/generate`, `/review`, `/invoice`, `POST /payments` (Idempotency-Key), `GET /payments/{id}/receipt.pdf`, `POST /payments/{id}/reverse`, `/allocate`, `POST /refunds`, `/refunds/{id}/approve`, `/reject`, `/process`, `GET /students/{id}/ledger`, `/open-invoices`, `POST /payments/online/order`, `/verify`, `POST /webhooks/razorpay/{institute_id}` |
| Accounting & payroll | `POST /expenses/{id}/decide`, `/mark-paid`, `POST /purchase-records/{id}/status`, `GET /accounting/cashbook`, `POST /financial-years/{id}/close`, `POST /payroll-periods/{id}/generate`, `/approve`, `POST /teacher-payables/{id}/decide`, `POST /payslips/{id}/pay`, `GET /payslips/{id}/pdf` |
| Library | `POST /library/issue`, `POST /library/loans/{id}/return` |
| Communication | `POST /announcements/{id}/publish`, `/archive`, `/acknowledge`, `GET /announcements/{id}/acknowledgements`, `GET /announcements/feed/mine`, `GET /messages/contacts`, `GET/POST /messages/threads`, `GET/POST /messages/threads/{id}`, `POST /messages/{id}/report`, `/moderate`, `GET /messages/reported`, `GET /notifications`, `/unread-count`, `POST /notifications/{id}/read`, `/read-all`, `GET/PUT /notifications/preferences`, `GET /notifications/push-public-key`, `POST /notifications/push-subscription`, `POST /notification-deliveries/{id}/retry`, `POST /surveys/{id}/status`, `/respond`, `GET /surveys/{id}/summary` |
| Reports | `GET /dashboard/admin`, `/teacher`, `/student`, `/parent`, `GET /reports`, `GET /reports/{key}?format=json\|csv\|xlsx\|pdf` (31 reports) |
| Platform | `GET /health`, `GET /ready`, `GET /search?q=`, `GET /imports/templates/{entity}`, `POST /imports/{entity}/preview`, `POST /imports/{job}/commit`, `GET /jobs/{id}/status`, `/download-link`, `GET /files/{signed-token}`, `POST /ai/generate`, `POST /ai/requests/{id}/review` |

Mapping to the brief's endpoint groups: `/teacher-payments` → `teacher-payouts` + `payslips/{id}/pay`;
`/payroll` → `payroll-periods`, `teacher-payables`, `payslips`; `/library` → `books`, `book-loans`,
`library-members`, `/library/*`; `/inventory` → `inventory-items`, `inventory-transactions`,
`assets`; `/question-bank` → `questions`; `/fee-plans` → `fee-plans`, `fee-agreements`;
`/settings` → `/settings/*`; `/webhooks` → `webhook-endpoints`, `/webhooks/razorpay/*`.
