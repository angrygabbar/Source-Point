# Teaching Management module handoff

## Requirement

Add a Teaching Management area for SourcePoint with teacher and student accounts, designed for online classes. Make common tasks easy to access and provide a way to record teaching and study effort. The product idea also called for accessible workflows, schedules, learning materials, assignments, progress, and feedback.

## Current implementation

The first implementation slice is in the working tree on `main` and has not been committed or deployed.

- Added `teacher` and `student` account roles, registration choices, server-side registration role validation, login redirection, and Teaching navigation.
- Admins have full Teaching access: they can view all classes, create their own classes, and perform teacher actions across classes, including scheduling, materials, assignments, grading, attendance, and effort logging.
- Admins can create Teacher and Student accounts from User Management, filter the user list by either role, and find accounts by username or email.
- When an admin creates a class, they must assign it to an active, approved Teacher account. Admins can also reassign an existing class to another eligible teacher.
- Teachers can create classes. Each class has a shareable invite code, subject/level/description, and IANA time zone.
- Students can join a class using its invite code. Class and submission pages verify teacher ownership or student enrollment before returning data or accepting changes.
- Teachers can schedule online sessions with a date, duration, meeting URL, and notes. Stored session times are UTC and rendered in the class time zone.
- Teachers can share materials as HTTP/HTTPS links.
- Teachers can publish assignments with instructions, an optional due date, and optional points. Students can submit or update a written response before the deadline. Teachers can grade submissions and leave feedback.
- Teachers can record attendance for enrolled students on each session as present, absent, late, or excused. Students can see their own attendance status. Only the class teacher can create or change records.
- Teachers and admins can update class name, subject, level, and description; archive a class; and reopen it later. Archived classes remain visible as history, stop accepting new students, and block new sessions, materials, assignments, submissions, and announcements.
- Teachers and admins can post class announcements; enrolled students can read them from the class page.
- Creating a class, scheduling a session, publishing an assignment, or posting an announcement queues an email to the assigned teacher, active enrolled students, and active admins. Student/admin recipients are blind-copied so their addresses are not exposed to one another. Email delivery uses the existing Celery/Brevo mail path.
- After a session ends, each enrolled student can leave or update a 1–5 rating and an optional comment. Teachers and admins can review the feedback on the session.
- Teachers and admins can create scheduled MCQ or short-answer tests, add up to 20 questions, and choose one or more active enrolled students from the class. Students receive an assignment email and can take the test during its availability window.
- MCQ tests are scored automatically. Short-answer submissions appear for teacher/admin review and grading. Submitting a test queues an email notification to the assigned teacher; admins are included through the existing mail helper.
- Teachers can record preparation, live teaching, grading, mentoring, and admin time. Students can record class study, assignment, revision, and practice time.
- Student effort logs are private by default. A student can explicitly share a class-linked log with that class's teacher. Personal/unlinked logs cannot be shared with a teacher.
- The new screens use labeled native controls, keyboard-operable buttons and disclosure widgets, visible focus rings, status messaging, and mobile responsive layout.
- Added migrations creating the Teaching tables and indexes, including separate attendance and announcement migrations.

## Main files

- templates/teaching/_test_manager.html, _student_tests.html, and take_test.html — teacher test creation/review, student assignment status, and test submission.
- templates/mail/teaching_test_assigned.html and teaching_test_submitted.html — student assignment and teacher submission notifications.
- migrations/versions/b671c2d9e40f_teaching_feedback_and_tests.py — session feedback, test, question, assignment, submission, and answer schema.

- `enums.py` — teacher/student roles.
- `models/teaching.py` — classes, enrollment, sessions, attendance, announcements, materials, assignments, submissions, and effort logs.
- `blueprints/teaching.py` — role-checked routes and class-level authorization, including admin access and teacher/admin attendance updates.
- `templates/teaching/home.html` — teacher/student workspace and summaries.
- `templates/teaching/class_detail.html` — class sessions, materials, assignments, submissions, roster, and effort views.
- `templates/mail/teaching_class_created.html`, `teaching_session_scheduled.html`, `teaching_assignment_created.html`, and `teaching_announcement.html` — class activity notices.
- `templates/teaching/_effort_form.html` — shared role-aware effort log form.
- `migrations/versions/c7b5e2a1f9d0_add_teaching_management_module.py` — schema migration, based on revision `8a1e4c6b2d90`.
- `migrations/versions/d1288e4a6f30_add_teaching_attendance.py` — attendance schema migration, based on the Teaching module migration.
- `migrations/versions/e4c19a7f2b6d_add_teaching_announcements.py` — class announcement schema migration.
- `blueprints/admin_users.py` and `templates/manage_users.html` — Teacher/Student account creation and role filtering in admin User Management.
- `app.py`, `blueprints/auth.py`, `blueprints/main.py`, `templates/layout.html`, `templates/login_register.html`, and `models/_init__.py` — app registration, login/register, navigation, and model discovery.

## Remaining roadmap

- Consider recurring sessions, announcement notifications/reminders, assignment attachments, progress summaries, and an effort report/export.
- Review whether teachers should invite students by email or require approval. At present, teachers share the generated code; admin-created accounts are approved immediately and registration follows SourcePoint's existing approval flow.
- Before production release, review and run the project's checks, then verify the migration revision graph and access boundaries against the production database and deployment process.
- This module has not been committed or deployed.

## Product and privacy decisions

- Student effort is not used for ranking or grading. The module only records minutes and an optional note.
- Student-to-teacher effort visibility requires an explicit checkbox and a selected class.
- Assignment submissions are text only; reopening or revising is allowed until the due date.
- Students can submit an assigned test once. MCQ scores are available immediately; short answers remain pending until graded.
- Scheduled reminder emails, video hosting, chat, guardian access, and file upload are not included yet.

## Handoff checkpoint

Start with the current working tree and this note. Do not reimplement the module from scratch. The developer asked to test the local build personally, so do not run tests or navigate the app. The feedback/test additions have not been committed or deployed.
