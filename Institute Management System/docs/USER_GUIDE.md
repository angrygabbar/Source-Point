# User guide

ClassFlow opens on `/login`. After sign-in each user lands on the dashboard of their portal
(administrator, teacher, student or parent). The left menu shows only what the user's role and
the institute's enabled modules allow. On mobile the menu collapses into a drawer and the app can
be installed (browser menu → *Install app / Add to Home screen*).

## First-time setup (institute administrator)

1. **Settings → General** – institute name, logo, contact, timezone, currency, invoice/receipt
   prefixes, financial-year start month.
2. **Settings → Feature flags** – turn modules on/off (library and inventory are off by default).
3. **Academic years**, **Branches** (if multi-branch), **Classrooms**, **Holidays**.
4. **Courses** → **Subjects** → **Batches** (capacity, course, academic year, branch).
5. **Teachers** (profile, qualification, compensation rule) → **Teacher assignments**
   (teacher ↔ batch ↔ subject).
6. **Students** and **Parents** (or **Imports** for CSV/XLSX bulk upload with preview and
   row-level errors). Link parents on the student page; use *Create login* for portal access.
7. **Enrollments** (student ↔ batch, optional subject selection) and **Fee agreements**
   (fee plan or custom amount, billing type: monthly, quarterly, annual, per subject, per course,
   per class, one-time, installment, custom; discounts/scholarships with reason).
8. **Schedules** (weekly recurring slots per batch/subject/teacher/room) → *Generate sessions* in
   **Timetable**. Conflicts (teacher, room, batch, holidays, teacher leave) are reported; overriding
   needs `schedules.override_conflict`.
9. **Users** – create staff logins and assign roles; **Roles** to customise permissions.
10. **Settings → Integrations** – optional email/SMS/WhatsApp/push/payments/AI/video providers.

## Daily operations

### Teachers
- **Dashboard** – today's classes, pending attendance, homework to review, upcoming exams.
- **Session page** (`Timetable` → click a session) – start/complete class, mark attendance
  (present/absent/late/excused/leave, *Mark all present*, remarks), topics covered, homework,
  materials, teacher self check-in. Submitted attendance is locked; changes go through
  *Request correction* or an authorised *Reopen*.
- **Study materials** – upload one or many files, set visibility (batch/subject/course/individual
  students), publish/schedule, upload new versions (old versions kept).
- **Homework** – create, target batches/students, attach files, publish; review submissions,
  grade with rubric/remarks, request resubmission.
- **Examinations / Question bank** – build papers from approved questions or enter marks offline;
  auto-grading for objective questions, manual grading queue for descriptive answers; compute →
  approve → publish results.
- **Syllabus / Lesson plans**, **Discussions** (answer doubts), **Messages**, **Leave requests**.

### Front desk / accountant
- **Admissions → Pipeline** – enquiries by stage; schedule follow-ups and demo classes, make an
  offer, *Convert* to student + enrollment + fee agreement.
- **Collect payment** – search a student, see open invoices and balance, record cash/UPI/card/bank/
  cheque payment (reference required for non-cash), allocate automatically (oldest first) or
  manually, print/download receipt PDF.
- **Invoices** – create, issue, download PDF; corrections via credit note / supplementary invoice;
  cancellation only with permission and reason.
- **Billing runs** – generate scheduled invoices for a period; review per-class charges (from
  attendance) then invoice approved charges.
- **Student ledger** – chronological invoices/payments/credits/refunds with running balance.
- **Refunds** – request → approve → process (separate permissions).
- **Expenses / Vendors / Purchases / Cashbook** – record and approve expenses, petty cash, bank
  register; close a financial year (blocks back-dated postings).

### HR / payroll
- **Teacher leaves** – approve/reject; approved leave flags sessions for substitution.
- **Payroll** – create a payroll period → *Generate* (from completed sessions and compensation
  rules: fixed monthly, per class, per hour or custom/manual amounts) → review payable
  entries (approve/reject, adjustments) → *Approve* → payslips → *Pay* (records payout and
  ledger) → payslip PDF.

### Students
- Dashboard: today's classes, attendance %, pending homework, upcoming exams, recent results,
  announcements, fee summary (if enabled).
- Materials (view/download), Homework (submit files/text before the deadline; resubmit when
  asked), Exams (online attempt with timer and auto-save; results after publication),
  Online learning (modules/lessons with progress and certificates), Discussions (ask doubts),
  Invoices/Payments (pay online if enabled), Messages, Notifications.

### Parents
- Child selector on the dashboard for parents with several children.
- Attendance, homework status, results/report cards, fee dues and receipts, announcements,
  teacher messages, parent-teacher meeting requests, consents, surveys.

## Reports
**Reports** lists the reports available to the user — academic (student/subject/batch/monthly
attendance, teacher attendance & hours, class completion, makeup sessions, teacher workload,
syllabus completion, homework submission, exam performance, student progress), financial (daily
and monthly collection, revenue by course/subject/batch/branch, outstanding fees, overdue invoices,
discounts & scholarships, refunds, expenses, income & expenditure, profit & loss, teacher payroll)
and business (admission conversion, student acquisition and retention, batch/classroom/teacher
utilisation, branch comparison, operational cost). Filter, view on screen, export CSV/XLSX/PDF.
Large list exports run in the background and appear under **Jobs**/notifications when ready.

## Search
Global search (top bar / **Search**) finds students, teachers, parents, batches, invoices,
receipts and enquiries within the user's permissions.

## Profile & security
**Profile** – change password, notification preferences (in-app/email/SMS/WhatsApp/push per
category), enable push on this device, active sessions (revoke), login history, download my data,
request account closure.
