# CLASSFLOW ERP

## Unified Autonomous Development Master Prompt

**Version:** 2.0\
**Product:** Enterprise Coaching Institute & Education Management ERP\
**Execution mode:** Autonomous implementation in the current workspace\
**Deployment target:** Docker Compose\
**Testing policy:** No testing or QA execution by the development agent

------------------------------------------------------------------------

# 0. MASTER DIRECTIVE

You are an autonomous enterprise software engineering team. Act as
solution architect, product designer, frontend engineer, backend
engineer, database architect, security engineer, DevOps engineer, and
technical writer.

Your task is to implement the complete ClassFlow ERP application
directly in the current project workspace.

**Do not respond with a plan instead of implementation. Do not ask the
user questions. Do not stop for approvals. Do not deliver only
wireframes, documentation, static screens, mock APIs, or a prototype.
Build the integrated application.**

Make sensible decisions whenever details are unspecified. Record
assumptions in `docs/ASSUMPTIONS.md`. Do not invent external credentials
or claim unavailable integrations are operational.

If the workspace contains an existing project, inspect it first and
preserve useful work. Avoid overwriting unrelated files. If the
workspace is empty, create the complete project.

The application must be designed as a cohesive product with shared data,
permissions, workflows, and audit history---not separate disconnected
modules.

## 0.1 No questions / autonomous decisions

-   Do not ask the user questions.
-   Do not request approval between phases.
-   Do not pause after architecture planning.
-   Do not ask the user to select technologies, layouts, colours,
    libraries, or implementation details.
-   Use the requirements and defaults in this document.
-   For unspecified details, select secure, maintainable defaults
    suitable for an Indian coaching institute.
-   For optional third-party services without credentials, implement a
    complete provider adapter and configuration UI, disabled by default.
-   Never fake successful payment, email, SMS, WhatsApp, calendar,
    video, or AI operations.

## 0.2 Testing prohibition

The user will perform testing separately in another environment.

**Do not execute testing or QA activities after development.** In
particular, do not run: - Unit, integration, end-to-end, acceptance, or
regression tests. - Playwright, Cypress, Selenium, browser QA, or manual
test scenarios. - Load, stress, performance, penetration, vulnerability,
or security tests. - Automated test suites or test scripts. - Test
commands as a final verification step.

Do not create a build/deployment workflow that automatically runs test
suites.

You may and must implement defensive programming, input validation,
authorization, database constraints, error handling, logging,
migrations, and recovery mechanisms. These are application
implementation requirements, not permission to execute tests.

Do not claim the application is tested, verified, secure by testing, or
production-validated. Final handover must explicitly state that testing
was intentionally not performed.

Normal implementation operations and non-test build/package commands may
be used when required to create deliverables. Do not launch a test
environment for QA.

## 0.3 Completion and continuity

Implement all requirements in this document in one unified project. If
the coding session is interrupted or context becomes limited: - Persist
progress in `IMPLEMENTATION_STATUS.md`. - Record completed modules,
remaining work, important files, migrations, decisions, and known
gaps. - Resume from that file without asking the user to repeat
requirements. - Do not replace implementation with a summary or stop
after writing the status file.

Do not mark a module complete if it contains placeholder screens, mock
business data, non-functional buttons, unconnected APIs, or missing
persistence.

------------------------------------------------------------------------

# 1. PRODUCT VISION AND BUSINESS PROFILE

**Product name:** ClassFlow ERP\
**Product type:** Enterprise coaching institute and education management
platform.

Initial operating profile:

  Parameter              Initial assumption
  ---------------------- ---------------------------------
  Institute type         Coaching / tuition classes
  Students               Below 50 initially
  Teachers               10--20 initially
  Batches                Multiple
  Courses and subjects   Multiple
  Billing                Mixed billing
  User portals           Admin, teacher, student, parent
  Country                India
  Default currency       INR
  Default timezone       Asia/Kolkata
  Default locale         English
  Date display           DD-MM-YYYY
  Deployment             Docker Compose

These are initial operating assumptions, **not hard-coded system
limits**. Do not impose fixed limits on students, teachers, batches,
branches, institutes, or academic years.

The platform should be capable of growing into a multi-branch,
multi-institute, SaaS-ready education ERP.

## 1.1 Product principles

1.  One central source of truth for all institute records.
2.  Four role-specific portals over a shared backend.
3.  Every class session has a permanent historical record.
4.  Student and teacher attendance are separate records.
5.  Financial transactions are traceable and auditable.
6.  Documents retain version history.
7.  Homework has a complete assignment-to-evaluation lifecycle.
8.  Historical records are preserved when students, teachers, batches,
    or fee plans change.
9.  All modules use shared identities and relational references.
10. External integrations are optional, configurable, and never
    simulated.

------------------------------------------------------------------------

# 2. TECHNOLOGY AND ARCHITECTURE

Use this stack unless an unavoidable compatibility issue requires a
documented alternative.

## 2.1 Frontend

-   Next.js with App Router.
-   React.
-   TypeScript strict mode.
-   Tailwind CSS.
-   shadcn/ui or equivalent accessible component system.
-   Lucide icons.
-   TanStack Query for server state.
-   React Hook Form.
-   Zod for client-side schemas.
-   Recharts for charts.
-   FullCalendar or equivalent calendar component.
-   PWA support.

## 2.2 Backend

-   Python 3.12 or compatible current stable version.
-   FastAPI.
-   SQLAlchemy 2.x.
-   Pydantic.
-   Alembic.
-   PostgreSQL.
-   Redis.
-   Celery or equivalent background worker.
-   OpenAPI/Swagger.

## 2.3 Storage and infrastructure

-   MinIO or compatible S3 object storage.
-   Docker and Docker Compose.
-   Nginx reverse proxy.
-   Persistent named volumes.
-   Structured logs.
-   Health and readiness endpoints.
-   Automated backup and restore scripts.
-   Configurable environment variables.

## 2.4 Architecture

Use a **modular monolith** with clearly separated domain modules. Do not
introduce microservices unnecessarily.

The frontend, API, database, object storage, cache, worker, and reverse
proxy must be separate deployable containers.

Keep domain boundaries clear so modules can evolve independently. Use a
common event/outbox mechanism for asynchronous side effects, but retain
transactional database logic for financial and other
consistency-critical operations.

------------------------------------------------------------------------

# 3. VISUAL DESIGN AND USER EXPERIENCE

The UI/UX quality is a top-level requirement. Create a premium, modern
enterprise SaaS experience---not a generic Bootstrap admin template.

## 3.1 Visual identity

Brand: **ClassFlow ERP**

Recommended design direction: - Deep navy / indigo primary. - Blue
secondary. - Teal accent. - Green success. - Amber warning. - Red
error. - Soft neutral backgrounds. - White surfaces with subtle borders
and restrained shadows. - Inter or comparable modern typography.

Use: - Consistent spacing and typography. - Clear visual hierarchy. -
Responsive grids. - Professional icons. - Attractive but restrained
charts. - Consistent buttons and form controls. - Accessible colour
contrast. - Clear loading, empty, success, and error states. - Subtle
transitions and hover states. - Responsive tables and mobile-friendly
cards. - Confirmation for destructive or sensitive operations.

Avoid excessive gradients, glassmorphism, animations, dense layouts, and
oversized decorative elements.

## 3.2 Application shell

Create: - Responsive sidebar. - Top navigation. - Institute logo and
name. - Branch selector where authorized. - Academic-year selector. -
Global search. - Notifications. - User profile and account menu. -
Breadcrumbs. - Quick actions.

## 3.3 Administrator dashboard

Display live database-backed widgets: - Active students. - Active
teachers. - Active batches. - Classes scheduled today. - Classes
completed today. - Student attendance today. - Teacher attendance
today. - Monthly fee collection. - Outstanding fees. - Upcoming
assignments. - Pending assignment evaluations. - Recent uploads. -
Recent activity.

Charts: - Monthly attendance trend. - Revenue trend. - Subject-wise
attendance. - Batch strength. - Teacher workload. - Admission
conversion, when CRM is enabled.

Sections: - Today's timetable. - Today's class status. - Students
needing attendance attention. - Upcoming fee dues. - Recent
transactions. - Recent activities.

Do not hardcode dashboard metrics. New installations must show
meaningful zero-data states and onboarding guidance.

## 3.4 Teacher dashboard

-   Today's timetable.
-   Upcoming classes.
-   Attendance pending.
-   Assigned batches and subjects.
-   Student lists.
-   Homework evaluations pending.
-   Upcoming assignment deadlines.
-   Recent materials.
-   Teaching workload.
-   Leave status.
-   Notifications.

## 3.5 Student dashboard

-   Today's classes.
-   Weekly timetable.
-   Attendance summary.
-   Recent materials.
-   Pending homework.
-   Submission history.
-   Grades and teacher feedback.
-   Upcoming deadlines.
-   Fee invoices and balances.
-   Announcements.

## 3.6 Parent dashboard

-   Linked-child selector.
-   Attendance overview.
-   Recent absences.
-   Upcoming classes.
-   Homework status.
-   Teacher feedback.
-   Academic progress.
-   Fee invoices and balances.
-   Payment history.
-   Notifications.

A parent may be linked to multiple students. Access must be restricted
to explicitly linked children.

## 3.7 Interaction standards

Every control must work. Implement search, filters, sorting, pagination,
date filtering, bulk actions where appropriate, exports, form
validation, confirmation dialogs, contextual menus, and notifications.

Never include inert buttons, fake charts, placeholder actions, or
navigation links that lead nowhere.

------------------------------------------------------------------------

# 4. IDENTITY, AUTHENTICATION, ROLES, AND PERMISSIONS

Implement: - Login and logout. - Password reset and change password. -
Short-lived access tokens. - Refresh-token rotation and revocation. -
Session management. - Account activation/deactivation. - Login
history. - User profile. - Role and permission administration.

Use Argon2id or an equivalent secure password hashing algorithm.

Use secure cookie handling where appropriate. Protect against CSRF when
cookie-based authentication is used.

## 4.1 Required roles

### Super administrator / platform administrator

For future SaaS operations and tenant administration. Access must be
tightly controlled.

### Institute administrator

Full access to the authorized institute and its branches.

### Branch administrator

Access limited to assigned branches and authorized operations.

### Teacher

Access to assigned classes, batches, subjects, enrolled students,
attendance, materials, homework, evaluations, leave, and own workload.

### Student

Access only to personal profile, enrollments, timetable, attendance,
authorized materials, assignments, submissions, grades, feedback,
invoices, and payments.

### Parent / guardian

Access only to explicitly linked children and permitted information.

### Optional future roles

Accountant, receptionist, academic coordinator, librarian, HR manager,
counsellor, and custom roles.

Implement role-based and resource-level authorization on the backend.
Frontend hiding is not authorization.

Add granular permissions for sensitive actions: - Attendance corrections
and reopening. - Invoice adjustment. - Payment reversal and refund. -
Student archival. - Grade modification. - Teacher compensation
approval. - Restricted counselling/disciplinary record access. - Audit
log access. - Tenant and branch administration.

------------------------------------------------------------------------

# 5. INSTITUTE, TENANT, BRANCH, AND ACADEMIC STRUCTURE

Build the hierarchy:

**Platform → Institute/Tenant → Branch → Academic Year → Course → Batch
→ Subject → Class Session**

A tenant may have multiple branches. Each branch may have independent
students, teachers, courses, batches, schedules, fee structures,
expenses, and reports.

Provide consolidated institute-level reporting for authorized users.

Enforce tenant and branch isolation in database relationships and API
authorization. Use composite constraints or equivalent safeguards to
prevent cross-tenant references.

Support institute branding, logos, theme colours, address, contact
information, timezone, currency, tax settings, and academic
configuration.

------------------------------------------------------------------------

# 6. STUDENT MANAGEMENT AND LIFECYCLE

Student fields: - UUID. - Institute and branch. - Unique student code. -
Full name. - Photograph. - Date of birth. - Optional gender. - Phone and
email. - Address. - Admission date. - Status. - Guardian information. -
Documents. - Emergency contacts. - Internal remarks.

Features: - Create, edit, activate, deactivate, archive. - Search and
filter. - CSV/Excel import and export. - Enrollment in multiple batches
and subjects. - Batch transfer. - Course transfer. - Branch transfer. -
Academic-year promotion. - Withdrawal and re-admission. - Student
profile timeline. - Attendance history. - Homework and exam history. -
Material access history. - Financial ledger. - Payment history. -
Certificates and ID card generation.

Profile tabs: 1. Overview. 2. Personal details. 3. Academic/enrollment
history. 4. Attendance. 5. Homework. 6. Examinations and results. 7.
Materials. 8. Fees and payments. 9. Documents. 10. Activity timeline.

Do not permanently delete students with historical academic or financial
records. Use archival and lifecycle status.

------------------------------------------------------------------------

# 7. TEACHER AND HR MANAGEMENT

Teacher fields: - UUID. - Institute and branch. - Unique teacher code. -
Name and photograph. - Contact details. - Qualifications. -
Specialization. - Joining date. - Employment status. - Compensation type
and amount. - Assigned subjects and batches. - Availability. -
Employment documents.

Teacher profile tabs: 1. Overview. 2. Subjects and batches. 3.
Timetable. 4. Attendance. 5. Classes conducted. 6. Leave. 7. Workload.
8. Compensation and payslips. 9. Documents. 10. Activity history.

HR capabilities: - Employee records. - Joining and exit workflow. -
Employment documents. - Leave applications and approvals. - Leave
balances. - Holiday calendar. - Salary structure. - Payroll periods. -
Payslips. - Salary revisions. - Deductions. - Performance reviews. -
Teacher appraisal. - Workload analysis. - Substitute allocation. -
Employee announcements.

Preserve teacher assignment history. A new assignment must not rewrite
historical class records.

------------------------------------------------------------------------

# 8. COURSES, SUBJECTS, BATCHES, AND ENROLLMENTS

Implement separate CRUD and management screens for: - Courses. -
Subjects. - Batches. - Batch-subject mappings. - Student enrollments. -
Enrollment-subject mappings. - Teacher assignments. - Academic years. -
Classrooms.

Support: - Multiple courses. - Multiple subjects per batch. - Multiple
teachers per subject/batch where appropriate. - One teacher across
multiple batches. - Students enrolled in multiple batches. - Different
fee agreements by subject or course. - Effective-date-based
assignments. - Capacity management. - Batch promotion and transfer. -
Historical enrollment records.

------------------------------------------------------------------------

# 9. TIMETABLE AND CLASS SESSION MANAGEMENT

This is the central operational entity of the application.

Implement: - Daily, weekly, and monthly calendar. - Teacher timetable. -
Batch timetable. - Subject timetable. - Classroom timetable. - Recurring
schedules. - One-time sessions. - Holidays and schedule exceptions. -
Rescheduling. - Cancellation. - Makeup classes. - Substitute teacher
assignment. - Conflict detection.

Each class session must have: - UUID. - Schedule reference. - Institute
and branch. - Academic year. - Batch. - Subject. - Scheduled teacher. -
Actual teacher or teachers. - Scheduled start and end. - Actual start
and end. - Classroom/location. - Status. - Cancellation reason. -
Remarks. - Creation and modification history.

Statuses: - Scheduled. - In progress. - Completed. - Cancelled. -
Postponed. - Teacher absent. - Pending verification.

Prevent overlapping teacher, batch, and classroom schedules. Authorized
overrides require a reason and audit record.

Preserve original scheduled teacher and actual substitute teacher
separately.

## 9.1 Class session as shared business anchor

Connect class sessions to: - Student attendance. - Teacher attendance. -
Materials. - Homework. - Lesson plans. - Syllabus progress. - Teacher
workload. - Per-class billing eligibility. - Reports and notifications.

When a class is completed, update related records through reliable
transactional operations and asynchronous events where appropriate.
Prevent duplicate financial charges or repeated notifications.

------------------------------------------------------------------------

# 10. STUDENT ATTENDANCE

Statuses: - Present. - Absent. - Late. - Excused. - Approved leave.

Features: - Load eligible students automatically. - Mark all present. -
Individual and bulk marking. - Remarks. - Save draft. - Submit and
lock. - Correction request. - Administrator reopening. - Correction
reason. - Original and corrected status history. - Marked by and
timestamps.

Determine eligibility using enrollment validity on the class date.

Do not silently count excused or approved leave as present. Report them
separately.

Calculate:
`Attendance percentage = Present eligible sessions / Total eligible sessions × 100`

Support student-wise, subject-wise, batch-wise, teacher-wise, monthly,
yearly, and academic-year reports.

Prevent duplicate student attendance per session.

------------------------------------------------------------------------

# 11. TEACHER ATTENDANCE

Record independently from student attendance.

Track: - Scheduled teacher. - Actual teacher. - Attendance status. -
Arrival and departure. - Teaching duration. - Substitute assignment. -
Leave. - Absence reason. - Class cancellation.

Do not infer teacher presence merely from a completed class. Do not
infer absence from a cancelled class.

Reports must compare scheduled sessions, conducted sessions, missed
sessions, substitute sessions, and actual teaching hours.

------------------------------------------------------------------------

# 12. STUDY MATERIAL AND DOCUMENT MANAGEMENT

Provide a centralized repository organized by:

Academic Year → Course → Batch → Subject → Category → Document.

Categories: - Notes. - Assignments. - Question papers. - Answer keys. -
Reference material. - Student submissions. - Other documents.

Maintain: - Document UUID. - Original filename. - Object-storage key. -
MIME type. - Size. - Checksum. - Uploader. - Subject, batch, academic
year. - Visibility and access policy. - Version number. - Description. -
Upload time. - Archive status.

Features: - Single and multiple uploads. - Version history. - Preview
where supported. - Secure download. - Search and filtering. - Soft
deletion and archive. - Storage quota. - Access and download logs. -
Version comparison metadata.

Never overwrite historical file contents. Use S3-compatible object
storage and keep credentials server-side.

Validate file size, MIME type, extension, and content where practical.
Restrict executable and dangerous file types by default.

------------------------------------------------------------------------

# 13. HOMEWORK AND ASSIGNMENT MANAGEMENT

Assignment targets: - Whole batch. - Selected students. -
Subject/batch. - Multiple batches where authorized.

Assignment fields: - Title. - Description. - Instructions. - Subject. -
Batch. - Teacher. - Assigned date. - Due date and time. - Maximum
marks. - Attachments. - Submission type. - Late submission rules. -
Publication status.

Lifecycle: Draft → Published → Submission Open → Under Evaluation →
Evaluated → Closed.

Student capabilities: - View assignment and instructions. - Download
attachments. - Save draft. - Upload multiple files. - Add remarks. -
Submit. - View submission history. - View marks and feedback. - Resubmit
when permitted.

Teacher capabilities: - Create and publish. - Edit unpublished
assignments. - View submission list. - Download files. - Grade and
comment. - Request resubmission. - Close assignment.

Statuses: - Not submitted. - Draft. - Submitted. - Late. - Under
review. - Evaluated. - Resubmission requested.

Retain previous submission versions. Store submission timestamps and
late status. Parents can view linked children's progress and feedback.

Dashboard metrics: - Assigned. - Submitted. - Not submitted. - Late. -
Pending evaluation. - Evaluated.

------------------------------------------------------------------------

# 14. EXAMINATION, ASSESSMENT, AND ACADEMIC PROGRESS

Implement: - Examination schedules. - Exam categories and terms. -
Question bank. - Questions by subject, chapter, difficulty, and type. -
MCQ, descriptive, numerical, and other configurable types. - Online
exams. - Offline exams. - Timers. - Randomized question/order
configuration. - Negative marking. - Objective auto-grading. - Manual
descriptive grading. - Marks entry. - Re-evaluation requests. - Grade
scales. - Rank lists. - Marksheets. - Report cards. - Subject-wise
performance. - Student progress history. - Remedial recommendations. -
Certificates.

Do not fabricate marks or make high-impact academic decisions
automatically. Provide teacher review and authorized approval.

------------------------------------------------------------------------

# 15. SYLLABUS AND LESSON PLANNING

Implement: - Course syllabus. - Subject chapters and topics. - Learning
outcomes. - Teacher lesson plans. - Planned versus completed lessons. -
Completion date. - Coverage percentage. - Delayed syllabus alerts. -
Chapter-level notes and resources. - Class-to-topic mapping. - Academic
calendar integration.

Show course, subject, batch, and teacher-wise syllabus progress.

------------------------------------------------------------------------

# 16. ADVANCED LMS AND ONLINE LEARNING

Implement: - Course modules. - Lessons. - Recorded lecture library. -
Learning resources. - Online class links. - Live class provider
integrations. - Discussion boards. - Doubt-solving sessions. - Practice
quizzes. - Video completion tracking where provider data permits. -
Learning progress. - Course completion records.

Use provider adapters for Zoom, Google Meet, or other meeting services.
Do not build a proprietary video conferencing system initially.

Do not claim video recording, streaming, or meeting creation works
unless the configured provider supports it.

------------------------------------------------------------------------

# 17. ADMISSION CRM

Implement a complete enquiry-to-enrollment workflow.

Features: - Enquiry registration. - Walk-in and online enquiries. - Lead
source. - Lead assignment. - Follow-up tasks and reminders. -
Counselling records. - Demo class scheduling. - Admission offers. -
Admission documents. - Admission fees. - Conversion tracking. - Lost
enquiry reasons. - Referral tracking. - Campaign tracking.

Suggested lifecycle: New Enquiry → Contacted → Counselling → Demo Class
→ Admission Offered → Enrolled / Lost.

Connect successful admission to student creation without duplicate
records.

------------------------------------------------------------------------

# 18. FEES, BILLING, ACCOUNTING, AND PAYMENTS

Support: - Monthly. - Quarterly. - Annual. - Per subject. - Per
course. - Per class. - Admission fees. - One-time fees. - Custom fee
plans. - Installments. - Scholarships. - Discounts. - Late fees. -
Advance payments.

Use student-specific fee agreements with effective dates.

Implement: - Fee plans and items. - Invoice generation. - Unique invoice
numbers. - Invoice PDF. - Payment collection. - Partial payments. -
Advance payments. - Payment allocations. - Receipts. - Refunds. - Credit
notes. - Adjustments. - Student ledger. - Outstanding and overdue
balances. - Financial reports.

Payment methods: - Cash. - UPI. - Bank transfer. - Cheque. -
Configurable online payment gateway.

Financial rules: - Use `NUMERIC(12,2)` or equivalent decimal-safe money
representation. - Store currency explicitly. - Prevent duplicate payment
references. - Use idempotency keys. - Maintain payment allocations. -
Never delete posted financial transactions. - Correct posted
transactions through reversal/adjustment entries. - Preserve immutable
financial history. - Use database transactions for invoice and payment
operations. - Never store UPI PINs, CVVs, or banking passwords. - Never
fabricate payment confirmation.

Per-class billing must use the student's effective fee agreement and
eligible completed sessions. Prevent duplicate student/session charges.
Allow administrator review before posting generated charges.

## 18.1 Accounting and operations

Implement: - Expense categories. - Expense records. - Vendor
management. - Purchase records and approvals. - Petty cash. -
Cashbook. - Bank transaction register. - Income and expenditure. -
Profit and loss reports. - Budgeting. - Revenue forecasts. - Financial
year closing. - GST/tax configuration. - Tax-ready invoices where
applicable.

Do not assume tax applicability. Keep tax rules configurable and based
on the institute's actual obligations.

## 18.2 Teacher compensation and payroll

Support: - Fixed monthly salary. - Per-class. - Per-hour. - Custom
compensation. - Payroll periods. - Payable entries. - Adjustments and
deductions. - Approval. - Payouts. - Payslips. - Payment history.

Calculate per-class compensation from approved actual teaching records,
not merely scheduled sessions.

------------------------------------------------------------------------

# 19. PARENT, STUDENT, AND TEACHER COMMUNICATION

Implement: - Institute announcements. - Batch announcements. -
Teacher-to-student communication. - Parent-teacher communication. -
Internal messaging. - Discussion threads. - Assignment comments. -
Parent-teacher meeting scheduling. - Meeting records. - Feedback
forms. - Student surveys. - Announcement acknowledgement. - Emergency
contact management. - Parent consent records.

Protect teacher personal contact details. Provide configurable
communication boundaries and moderation/reporting controls.

------------------------------------------------------------------------

# 20. NOTIFICATION ENGINE

Events: - Admission. - Student absence. - Teacher absence. - Class
cancellation/rescheduling. - Material upload. - Assignment
publication. - Homework deadline. - Submission. - Evaluation. - Fee
due/overdue. - Payment received. - Announcement. - Leave approval.

Channels: - In-app. - Email. - SMS. - WhatsApp Business API. - Push
notifications where supported.

Implement: - User preferences. - Event templates. - Delivery history. -
Retry queue. - Failed-delivery status. - Scheduled notifications. -
Provider adapters. - Background processing.

External channels are disabled by default until credentials are
configured. Never simulate delivery.

------------------------------------------------------------------------

# 21. LIBRARY, CLASSROOM, INVENTORY, AND ASSETS

Implement optional modules for: - Book catalogue. - Library members. -
Issue and return. - Due dates and reminders. - Lost/damaged books. -
Digital resources. - Classroom management. - Room capacity. - Room
allocation. - Projector and equipment inventory. - Computers and
devices. - Stationery inventory. - Asset assignment. - Asset
maintenance. - Purchase history. - Vendor records.

Use classroom allocation in timetable conflict detection.

------------------------------------------------------------------------

# 22. REPORTS AND ANALYTICS

Academic reports: - Student attendance. - Subject and batch
attendance. - Teacher attendance. - Class completion and cancellation. -
Makeup sessions. - Teacher workload. - Syllabus completion. - Homework
submission. - Assignment evaluation. - Examination performance. -
Student progress.

Financial reports: - Daily and monthly collection. - Revenue by course,
subject, batch, and branch. - Outstanding fees. - Overdue invoices. -
Student ledger. - Discounts and scholarships. - Refunds. - Expenses. -
Income and expenditure. - Profit and loss. - Teacher payroll.

Business reports: - Admission conversion. - Student retention. - Student
acquisition. - Batch utilization. - Classroom utilization. - Teacher
utilization. - Branch comparison. - Operational cost.

All reports must use actual persisted data and support relevant filters
and exports.

Exports: - CSV. - Excel. - PDF.

Respect authorization and institute/branch scope in every report.

------------------------------------------------------------------------

# 23. GLOBAL SEARCH, TIMELINES, AND AUDIT

Global search across: - Students. - Teachers. - Parents. - Courses. -
Subjects. - Batches. - Classes. - Materials. - Assignments. -
Invoices. - Payments. - Admissions.

Search results must respect permissions.

Implement entity activity timelines and audit logs.

Audit important changes with: - Actor. - Institute and branch. - Entity
type and ID. - Action. - Old and new values where appropriate. -
Timestamp. - Request/correlation ID. - Reason for sensitive changes.

Audit logs should be append-only to normal application users.

------------------------------------------------------------------------

# 24. AI AND AUTOMATION READINESS

Create provider-independent, optional AI adapters for: - Question
generation. - Assignment drafting. - Study material summaries. -
Document extraction. - Academic progress summaries. - Learning
assistance. - Knowledge-base Q&A over authorized institute material. -
Administrative report drafting.

AI requirements: - Disabled by default. - Administrator configuration. -
Usage limits and cost tracking. - Role-based access. - Privacy
controls. - Human approval for important decisions. - Clear AI-generated
labels. - No fabricated grades or academic records. - No external
sharing of student data without appropriate authorization.

Implement deterministic automations for: - Attendance alerts. - Fee
reminders. - Homework reminders. - Follow-up reminders. - Syllabus delay
alerts. - Pending evaluation alerts. - Scheduled reports.

------------------------------------------------------------------------

# 25. MULTI-TENANT, SAAS, AND WHITE-LABEL READINESS

Prepare: - Institute/tenant hierarchy. - Multiple branches. - Tenant
isolation. - Branch-specific roles. - Consolidated reports. - Branding
and logos. - Theme settings. - Custom fields. - Feature flags. - Module
entitlements. - Storage quotas. - Usage tracking. - Subscription
plans. - Trial status. - Subscription lifecycle. - SaaS subscription
invoices.

Do not require SaaS billing to operate a single self-hosted institute.
Keep commercial subscription management separate from student fee
billing.

------------------------------------------------------------------------

# 26. MOBILE AND PWA

Implement responsive PWA capabilities: - Installable application. -
Mobile navigation. - Quick attendance. - Mobile file uploads. - Camera
document capture. - Push notifications where supported. - Offline
drafts. - Controlled synchronization. - Conflict detection and
resolution. - Responsive tables and dashboards.

Do not cache sensitive personal or financial data insecurely. Make APIs
reusable by future native Android/iOS applications.

------------------------------------------------------------------------

# 27. API DESIGN

Use REST APIs under `/api/v1`.

Required endpoint groups: - `/auth` - `/users` - `/institutes` -
`/branches` - `/students` - `/teachers` - `/parents` - `/courses` -
`/subjects` - `/batches` - `/enrollments` - `/teacher-assignments` -
`/schedules` - `/class-sessions` - `/attendance` - `/materials` -
`/assignments` - `/submissions` - `/examinations` - `/question-bank` -
`/syllabus` - `/admissions` - `/fee-plans` - `/invoices` - `/payments` -
`/refunds` - `/expenses` - `/vendors` - `/teacher-payments` -
`/payroll` - `/library` - `/inventory` - `/notifications` -
`/announcements` - `/messages` - `/reports` - `/integrations` -
`/webhooks` - `/settings` - `/audit-logs`

Every endpoint must include appropriate: - HTTP method. - Request and
response schema. - Validation. - Authorization. - Error handling. -
Pagination. - Filtering and sorting. - Idempotency for retry-sensitive
operations.

Publish OpenAPI documentation. Do not expose secrets or internal stack
traces.

------------------------------------------------------------------------

# 28. DATABASE DESIGN

Use PostgreSQL, UUID primary keys, foreign keys, indexes, unique
constraints, check constraints, and transactional operations.

Use: - `UUID` identifiers. - `TIMESTAMPTZ` timestamps. - `DATE` for
calendar dates. - `NUMERIC(12,2)` for money. - Explicit currency
codes. - JSONB only for genuinely flexible metadata, not core relational
relationships.

Required table domains include:

### Tenant and academic structure

-   institutes
-   branches
-   academic_years
-   courses
-   subjects
-   batches
-   batch_subjects
-   classrooms

### Identity

-   users
-   roles
-   permissions
-   user_roles
-   refresh_tokens
-   login_history
-   students
-   teachers
-   parents
-   student_parents

### Enrollment and staffing

-   student_enrollments
-   enrollment_subjects
-   teacher_assignments
-   teacher_availability
-   teacher_leaves
-   employment_records

### Scheduling and attendance

-   class_schedules
-   class_schedule_exceptions
-   class_sessions
-   class_session_teachers
-   student_attendance
-   teacher_attendance
-   attendance_corrections
-   attendance_audit_logs

### Learning

-   materials
-   material_versions
-   material_access
-   file_download_logs
-   assignments
-   assignment_targets
-   assignment_attachments
-   submissions
-   submission_versions
-   assignment_grades
-   syllabus_chapters
-   lesson_plans
-   examinations
-   questions
-   exam_attempts
-   exam_results

### Admissions

-   enquiries
-   leads
-   follow_ups
-   demo_classes
-   admission_records

### Financial

-   fee_plans
-   fee_plan_items
-   student_fee_agreements
-   invoices
-   invoice_items
-   payments
-   payment_allocations
-   refunds
-   credit_notes
-   ledger_entries
-   expenses
-   vendors
-   purchase_records
-   compensation_rules
-   teacher_payable_entries
-   teacher_payouts
-   payroll_periods
-   payslips

### Communication and resources

-   notifications
-   notification_preferences
-   notification_deliveries
-   announcements
-   messages
-   parent_meetings
-   books
-   book_loans
-   assets
-   inventory_items
-   asset_assignments
-   maintenance_records

### Platform

-   audit_logs
-   application_settings
-   feature_flags
-   integration_configs
-   api_keys
-   webhook_endpoints
-   webhook_deliveries
-   subscription_plans
-   tenant_subscriptions
-   usage_records
-   background_jobs
-   event_outbox

Implement full relationships, indexes, constraints, and Alembic
migrations.

Critical safeguards: - No duplicate attendance per session/student. - No
duplicate payment transaction reference. - No cross-tenant foreign
references. - Valid enrollment date ranges. - Valid fee and payment
allocations. - Unique document versions. - No hard deletion of posted
financial transactions. - No hard deletion of historical class
sessions. - Prevent duplicate per-class billing. - Use transactions for
payment, attendance submission, and other multi-step operations.

Store timestamps consistently in UTC; display in the institute timezone.

------------------------------------------------------------------------

# 29. SECURITY AND PRIVACY

Implement: - Argon2id password hashing. - Secure session management. -
Refresh-token rotation. - RBAC and object-level authorization. - Tenant
and branch isolation. - Secure file upload and signed download. - Rate
limiting. - Input validation. - SQL injection prevention. - XSS
protection. - CSRF protection where applicable. - Secure headers. - CORS
allowlists. - Audit logs. - Login monitoring. - Session revocation. -
Secrets management. - Encrypted backups. - Data export and account
closure workflows. - Configurable retention.

Sensitive counselling, disciplinary, financial, and personal records
require explicit permissions.

Follow applicable Indian privacy and data-protection requirements. Do
not store UPI PINs, card CVVs, or bank credentials.

------------------------------------------------------------------------

# 30. DOCKER AND DEPLOYMENT

Required services: 1. `frontend` 2. `backend` 3. `postgres` 4. `redis`
5. `minio` 6. `worker` 7. `nginx`

Create: - Frontend Dockerfile. - Backend Dockerfile. -
`docker-compose.yml`. - `docker-compose.prod.yml`. - Nginx
configuration. - `.env.example`. - `.gitignore`. - Health checks. -
Restart policies. - Dedicated network. - Persistent named volumes. -
Resource limits where appropriate. - Non-root containers where
practical. - Pinned compatible image versions. - Migration process. -
Backup scripts. - Restore scripts. - Logging configuration.

Persist PostgreSQL, Redis, and MinIO data in named volumes.

Do not expose PostgreSQL or Redis publicly. Do not expose MinIO
administration publicly. Expose only the Nginx application entry point.

Make host ports configurable.

Support Docker Desktop on macOS and standard Linux Docker hosts. Do not
assume a particular host port or hard-code user-specific filesystem
paths.

Use separate development and production configurations.

------------------------------------------------------------------------

# 31. BACKUP AND RECOVERY

Implement: - Daily PostgreSQL logical backups. - Timestamped compressed
backups. - Retention policy. - Backup error handling. - Object-storage
backup or replication. - Version metadata preservation. - Encryption. -
Restore script. - Recovery documentation.

Keep database and object-storage backups coordinated. A database backup
alone is not a complete backup of uploaded documents.

Never claim a backup was verified or restored unless that operation was
actually performed.

------------------------------------------------------------------------

# 32. FEATURE FLAGS AND CONFIGURATION

Implement centralized settings and feature flags for: - Attendance. -
Homework. - Study materials. - Billing. - Teacher compensation. -
Examinations. - LMS. - Admissions CRM. - HR/payroll. - Parent portal. -
Library. - Inventory. - Multiple branches. - SaaS subscription
management. - Email. - SMS. - WhatsApp. - Online payments. - AI
services. - Video meeting integrations.

Disabled modules must not create broken navigation or backend errors.

Core authentication, authorization, audit, and data-integrity safeguards
must never be disabled.

Provide administrator controls for permitted settings.

------------------------------------------------------------------------

# 33. IMPORT AND EXPORT

Implement templates, import, validation, preview, and commit workflows
for: - Students. - Teachers. - Courses. - Subjects. - Batches. -
Enrollments. - Historical attendance where supported.

Prevent duplicates and provide row-level error feedback.

Exports: - Student records. - Attendance. - Timetable. - Homework. -
Examination results. - Invoices. - Payments. - Financial reports. -
Teacher payroll.

Respect user permissions and active filters. Use background jobs for
large exports.

------------------------------------------------------------------------

# 34. OBSERVABILITY AND RELIABILITY

Implement: - Structured logs. - Request/correlation IDs. - Application
error handling. - Health and readiness endpoints. - Background job
status. - Failed notification queue. - External integration delivery
status. - Storage usage. - Database connection handling. - Graceful
shutdown. - Retry policy for appropriate asynchronous operations.

Do not expose stack traces, secrets, SQL statements, or sensitive
personal information in user-facing errors or logs.

------------------------------------------------------------------------

# 35. PROJECT STRUCTURE

Use a clean, maintainable structure similar to:

``` text
classflow-erp/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── services/
│   │   ├── types/
│   │   └── styles/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── modules/
│   │   ├── workers/
│   │   └── main.py
│   ├── migrations/
│   ├── Dockerfile
│   └── requirements.txt
├── infrastructure/
│   ├── nginx/
│   ├── scripts/
│   └── monitoring/
├── docs/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── IMPLEMENTATION_STATUS.md
└── README.md
```

Adapt the structure as needed, but retain clear module boundaries.

------------------------------------------------------------------------

# 36. REQUIRED DOCUMENTATION

Create documentation that reflects the actual implementation:

1.  `README.md`
2.  `docs/ARCHITECTURE.md`
3.  `docs/DATABASE_SCHEMA.md`
4.  `docs/API_DOCUMENTATION.md`
5.  `docs/DEPLOYMENT_GUIDE.md`
6.  `docs/CONFIGURATION_GUIDE.md`
7.  `docs/USER_GUIDE.md`
8.  `docs/BACKUP_RESTORE_GUIDE.md`
9.  `docs/SECURITY_GUIDE.md`
10. `docs/ASSUMPTIONS.md`
11. `docs/INTEGRATIONS_GUIDE.md`
12. `docs/IMPLEMENTATION_HANDOVER.md`
13. `IMPLEMENTATION_STATUS.md`

Include actual commands, environment variables, migration instructions,
administrator bootstrap instructions, storage configuration,
backup/restore instructions, and external credentials needed.

Do not document imaginary or unimplemented functionality as completed.

------------------------------------------------------------------------

# 37. IMPLEMENTATION EXECUTION SEQUENCE

Work continuously without requesting approval.

1.  Inspect workspace and preserve useful existing work.
2.  Create project structure and record assumptions.
3.  Implement tenant, institute, branch, identity, and permission
    foundation.
4.  Implement complete database models and Alembic migrations.
5.  Implement backend business modules and APIs.
6.  Implement frontend design system and application shell.
7.  Implement all four portals.
8.  Implement academic, class, attendance, materials, homework,
    examination, and LMS workflows.
9.  Implement admission CRM, HR, finance, accounting, payroll, and
    resources.
10. Implement notifications, reports, search, audit, and integrations.
11. Implement feature flags, tenant/branch controls, and SaaS readiness.
12. Implement Docker, Nginx, environment configuration, backup, and
    restore.
13. Write complete documentation.
14. Update implementation status and final handover.

Do not stop after writing a plan. Continue creating the actual files.

If a requirement cannot be fully implemented because a third-party
credential or provider account is unavailable, implement the complete
adapter, configuration mechanism, disabled state, and documentation.
State the dependency clearly.

------------------------------------------------------------------------

# 38. FINAL DELIVERABLES

The workspace must contain: - Complete frontend application. - Four
functional role-based portals. - Complete backend and REST APIs. -
Database models and migrations. - Business workflows and validation. -
Secure file storage integration. - Homework and examination workflows. -
Fee billing and accounting. - Teacher HR and payroll. - Admission CRM. -
Communication and notifications. - Reports and analytics. - Multi-tenant
and multi-branch foundations. - AI and external integration adapters. -
Dockerfiles and Compose configurations. - Nginx configuration. -
Environment template. - Backup and restore scripts. - Complete
documentation. - Implementation status and handover.

No core module may be represented by static screens, hardcoded values,
fake APIs, or placeholder buttons.

------------------------------------------------------------------------

# 39. FINAL ACCEPTANCE CHECKLIST

Mark each item complete only when its actual implementation exists.

## Core platform

-   [ ] Four portals.
-   [ ] Authentication and session management.
-   [ ] RBAC and resource-level permissions.
-   [ ] Tenant and branch isolation.
-   [ ] Institute branding and settings.
-   [ ] Feature flags.

## People and academics

-   [ ] Students and lifecycle.
-   [ ] Teachers and HR.
-   [ ] Parents and guardian linking.
-   [ ] Courses, subjects, batches.
-   [ ] Enrollments.
-   [ ] Admissions CRM.
-   [ ] Academic years.
-   [ ] Syllabus and lesson planning.

## Class operations

-   [ ] Timetable.
-   [ ] Class sessions.
-   [ ] Student attendance.
-   [ ] Teacher attendance.
-   [ ] Substitution.
-   [ ] Makeup classes.
-   [ ] Class history.

## Learning

-   [ ] Materials and file versioning.
-   [ ] Homework.
-   [ ] Student submissions.
-   [ ] Evaluation and feedback.
-   [ ] Examinations.
-   [ ] Question bank.
-   [ ] Results and marksheets.
-   [ ] LMS and online learning integrations.

## Finance

-   [ ] Mixed fee plans.
-   [ ] Invoices.
-   [ ] Partial payments.
-   [ ] Payment allocations.
-   [ ] Receipts.
-   [ ] Refunds and adjustments.
-   [ ] Student ledger.
-   [ ] Expenses and vendors.
-   [ ] Accounting reports.
-   [ ] Teacher compensation and payroll.

## Operations

-   [ ] Parent communication.
-   [ ] Notifications.
-   [ ] Library.
-   [ ] Inventory.
-   [ ] Classrooms and assets.
-   [ ] Reports and analytics.
-   [ ] Global search.
-   [ ] Audit history.
-   [ ] Import/export.

## Platform and deployment

-   [ ] API documentation.
-   [ ] Dockerfiles.
-   [ ] Docker Compose.
-   [ ] Nginx.
-   [ ] Persistent volumes.
-   [ ] Health endpoints.
-   [ ] Environment configuration.
-   [ ] Backup and restore.
-   [ ] Security documentation.
-   [ ] User documentation.
-   [ ] Implementation handover.

------------------------------------------------------------------------

# 40. FINAL COMMAND TO THE DEVELOPMENT AGENT

**BEGIN IMPLEMENTATION IMMEDIATELY.**

Create the complete ClassFlow ERP application in the current workspace.

Do not respond with another proposal, plan, list of questions,
wireframe, or architecture-only document.

Do not ask the user to choose implementation details.

Do not stop after partial modules.

Do not substitute documentation for code.

Do not leave core modules disconnected.

Implement the entire system as one cohesive, persistent, Docker-ready
application.

**Do not execute tests or QA after development.** Testing will be
performed separately by the user.

At completion, provide a concise handover containing: - Implemented
modules. - Project directory structure. - Database migration location. -
Startup and deployment commands. - Administrator bootstrap process. -
Environment configuration. - External integrations requiring
credentials. - Backup and restore instructions. - Known unimplemented
items or limitations. - Explicit statement that testing was
intentionally not performed.

The final outcome must be the actual integrated ClassFlow ERP software
project, not a plan to build it.
