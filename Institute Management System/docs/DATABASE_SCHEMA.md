# Database schema

PostgreSQL 16. 140 tables generated from `backend/app/models/*.py` and created by the Alembic
baseline `backend/migrations/versions/0001_initial.py`.

## Conventions

- `UUID` primary keys (`id`), `TIMESTAMPTZ` `created_at`/`updated_at` (UTC), `DATE` for calendar dates.
- Money: `NUMERIC(12,2)` with explicit `currency` columns (default `INR`).
- Tenant tables carry `institute_id` (FK `institutes`, `ON DELETE RESTRICT`); branch-scoped tables carry `branch_id`.
- `created_by_id` / `updated_by_id` on most business tables; `is_archived`/`archived_at` for soft archival.
- Enumerations are `VARCHAR` with `CHECK` constraints (non-native enums) so values can be extended by migration.
- JSONB only for flexible metadata (options, answers, custom fields, audit diffs, settings).
- Constraint naming convention: `uq_`, `fk_`, `pk_`, `ix_` (see `models/base.py`).

## Domains and tables

| Domain | Tables |
|---|---|
| Tenancy & academic structure | institutes, branches, academic_years, courses, subjects, batches, batch_subjects, classrooms, holidays |
| Identity | users, roles, permissions, role_permissions, user_roles, refresh_tokens, login_history, password_reset_tokens, students, teachers, parents, student_parents, counselling_records |
| Enrollment & staffing | student_enrollments, enrollment_subjects, teacher_assignments, teacher_availability, teacher_leaves, leave_balances, employment_records, performance_reviews |
| Scheduling & attendance | class_schedules, class_schedule_exceptions, class_sessions, class_session_teachers, student_attendance, teacher_attendance, attendance_corrections, attendance_audit_logs |
| Learning | documents, materials, material_versions, material_access, file_download_logs, assignments, assignment_targets, assignment_attachments, submissions, submission_versions, submission_files, assignment_grades, assignment_comments, syllabus_chapters, syllabus_progress, lesson_plans |
| LMS | lms_modules, lms_lessons, lesson_progress, course_completions, discussion_threads, discussion_posts, online_meetings |
| Examinations | grade_scales, examinations, questions, exam_questions, exam_attempts, exam_responses, exam_results, re_evaluation_requests |
| Admissions | campaigns, leads, enquiries, follow_ups, demo_classes, admission_records |
| Finance | fee_plans, fee_plan_items, student_fee_agreements, invoices, invoice_items, billable_charges, payments, payment_allocations, refunds, credit_notes, ledger_entries, number_sequences |
| Accounting | vendors, expense_categories, expenses, purchase_records, cashbook_entries, bank_transactions, budgets, financial_years, tax_rates |
| Payroll | compensation_rules, payroll_periods, teacher_payable_entries, payslips, teacher_payouts |
| Communication | announcements, announcement_acknowledgements, message_threads, message_thread_participants, messages, parent_meetings, surveys, survey_responses, parent_consents, notifications, notification_preferences, notification_templates, notification_deliveries, push_subscriptions |
| Resources | books, library_members, book_loans, inventory_items, inventory_transactions, assets, asset_assignments, maintenance_records |
| Platform | audit_logs, application_settings, feature_flags, custom_field_definitions, integration_configs, api_keys, webhook_endpoints, webhook_deliveries, inbound_webhook_events, subscription_plans, tenant_subscriptions, saas_invoices, usage_records, background_jobs, event_outbox, idempotency_records, ai_requests |

Notes on naming vs. the brief: `leads` are people (deduplicated by phone/email) and `enquiries`
are their course enquiries moving through the pipeline. `billable_charges` holds per-class charges
awaiting review. `documents` stores versioned files attached to students, teachers, parents,
expenses and admissions.

## Integrity safeguards

| Rule | Mechanism |
|---|---|
| One attendance row per session/student | `UNIQUE(session_id, student_id)` on `student_attendance` (and per teacher on `teacher_attendance`) |
| No duplicate payment references | partial unique index `(institute_id, method, reference_number)` for non-cash; unique `gateway_payment_id`; unique `(institute_id, idempotency_key)` |
| No duplicate per-class billing | `UNIQUE(student_id, session_id)` on `billable_charges`; partial unique `(teacher_id, session_id)` on payable entries |
| No duplicate periodic invoice | partial unique `(agreement_id, period_start)` for scheduled invoices |
| No duplicate generated sessions | partial unique `(schedule_id, session_date)` for regular sessions |
| One active enrollment per student/batch | partial unique index where `status='active'` |
| Valid date ranges | `CHECK (end_date IS NULL OR end_date >= start_date)` on enrollments, assignments, agreements, schedules, leaves … |
| Valid money/allocations | `CHECK` amount > 0 / ≥ 0, `unallocated_amount BETWEEN 0 AND amount`, invoice totals ≥ 0 |
| Unique document versions | `UNIQUE(material_id, version_number)`, `UNIQUE(submission_id, version_number)`, unique object keys |
| Append-only ledger & audit | triggers `cf_block_change` on `ledger_entries`, `audit_logs` (UPDATE/DELETE raise) |
| No deletion of history | `cf_block_delete` triggers on payments, payment_allocations, refunds, credit_notes, class_sessions, student/teacher attendance, payouts, payslips, material/submission versions, exam_results |
| Posted invoices immutable | `cf_invoice_guard` blocks changes to amounts/number/student/date once not draft; `cf_invoice_item_guard` blocks item edits |
| Posted payments immutable | `cf_payment_guard` blocks changes to amount/student/receipt/date/method (status changes allowed for reversal) |
| Cross-tenant references | every FK written through the API is checked against the caller's `institute_id` (`crud/engine.py::validate_references`); workflow routers load parents via `get_tenant_obj` |
| Closed financial years | `services/finance.py::ensure_period_open` blocks postings dated inside a closed year |

## Migrations

```bash
# apply (runs automatically via the `migrate` service on compose up)
docker compose exec backend python -m app.cli migrate
# create a new revision after changing models
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

The baseline revision materialises the metadata as of this release; all subsequent changes must be
new revisions.
