"""Permission catalogue and default role definitions."""

MODULES: dict[str, str] = {
    "institutes": "Institute profile & branding",
    "branches": "Branches",
    "academic_years": "Academic years",
    "classrooms": "Classrooms",
    "courses": "Courses",
    "subjects": "Subjects",
    "batches": "Batches",
    "students": "Students",
    "teachers": "Teachers",
    "parents": "Parents & guardians",
    "enrollments": "Enrollments",
    "teacher_assignments": "Teacher assignments",
    "schedules": "Timetable schedules",
    "sessions": "Class sessions",
    "attendance": "Student attendance",
    "teacher_attendance": "Teacher attendance",
    "materials": "Study materials",
    "documents": "Documents",
    "assignments": "Homework & assignments",
    "submissions": "Submissions",
    "syllabus": "Syllabus",
    "lesson_plans": "Lesson plans",
    "exams": "Examinations",
    "questions": "Question bank",
    "results": "Exam results",
    "lms": "LMS",
    "discussions": "Discussions",
    "admissions": "Admissions CRM",
    "fees": "Fee plans & agreements",
    "invoices": "Invoices",
    "payments": "Payments",
    "refunds": "Refunds & credit notes",
    "expenses": "Expenses",
    "vendors": "Vendors & purchases",
    "accounting": "Accounting",
    "payroll": "Payroll & compensation",
    "leaves": "Leave management",
    "hr": "HR records",
    "library": "Library",
    "inventory": "Inventory",
    "assets": "Assets",
    "announcements": "Announcements",
    "messages": "Messaging",
    "meetings": "Parent meetings",
    "surveys": "Feedback & surveys",
    "notifications": "Notifications",
    "reports": "Reports",
    "users": "Users",
    "roles": "Roles & permissions",
    "settings": "Settings & feature flags",
    "integrations": "Integrations",
    "webhooks": "Webhooks & API keys",
    "audit": "Audit logs",
    "imports": "Import / export",
    "ai": "AI assistant",
    "saas": "Subscriptions",
    "counselling": "Counselling & disciplinary",
}

ACTIONS = ("read", "read_own", "write", "write_own", "delete")

SENSITIVE: dict[str, str] = {
    "attendance.reopen": "Reopen submitted attendance",
    "attendance.correct_approve": "Approve attendance corrections",
    "invoices.adjust": "Adjust invoices (credit notes / supplementary)",
    "invoices.cancel": "Cancel invoices",
    "payments.reverse": "Reverse payments",
    "refunds.approve": "Approve and process refunds",
    "students.archive": "Archive / withdraw students",
    "students.sensitive": "View internal student remarks",
    "grades.modify": "Modify finalised grades",
    "results.approve": "Approve and publish exam results",
    "payroll.approve": "Approve teacher compensation & payroll",
    "counselling.restricted": "Access confidential counselling/disciplinary records",
    "audit.read_all": "Read audit logs",
    "tenant.admin": "Institute / tenant administration",
    "branch.admin": "Branch administration",
    "teachers.contact": "View teacher personal contact details",
    "admissions.counselling": "View counselling notes",
    "schedules.override_conflict": "Override timetable conflicts",
    "finance.close_year": "Close financial year",
    "platform.admin": "Platform (SaaS) administration",
}


def all_permission_codes() -> list[tuple[str, str, str, bool]]:
    rows: list[tuple[str, str, str, bool]] = []
    for module, label in MODULES.items():
        for action in ACTIONS:
            rows.append((f"{module}.{action}", module, f"{label}: {action.replace('_', ' ')}", False))
    for code, desc in SENSITIVE.items():
        rows.append((code, code.split(".")[0], desc, True))
    return rows


def _all(*modules: str, actions=("read", "write", "delete")) -> set[str]:
    return {f"{m}.{a}" for m in modules for a in actions}


ALL_MODULE_PERMS = {code for code, *_ in all_permission_codes()}

_ACADEMIC = ("academic_years", "classrooms", "courses", "subjects", "batches", "enrollments", "teacher_assignments",
             "schedules", "sessions", "attendance", "teacher_attendance", "materials", "documents", "assignments",
             "submissions", "syllabus", "lesson_plans", "exams", "questions", "results", "lms", "discussions")
_FINANCE = ("fees", "invoices", "payments", "refunds", "expenses", "vendors", "accounting", "payroll")

DEFAULT_ROLES: dict[str, dict] = {
    "institute_admin": {
        "name": "Institute administrator",
        "portal": "admin",
        "permissions": (ALL_MODULE_PERMS - {"platform.admin"}),
    },
    "branch_admin": {
        "name": "Branch administrator",
        "portal": "admin",
        "permissions": (
            ALL_MODULE_PERMS
            - {"platform.admin", "tenant.admin", "saas.read", "saas.write", "saas.delete", "institutes.write",
               "institutes.delete", "integrations.write", "integrations.delete", "webhooks.write", "webhooks.delete",
               "finance.close_year", "roles.write", "roles.delete"}
        ),
    },
    "teacher": {
        "name": "Teacher",
        "portal": "teacher",
        "permissions": {
            "courses.read", "subjects.read", "batches.read_own", "classrooms.read", "academic_years.read",
            "students.read_own", "parents.read_own", "enrollments.read_own", "teacher_assignments.read_own",
            "schedules.read_own", "sessions.read_own", "sessions.write_own",
            "attendance.read_own", "attendance.write_own", "teacher_attendance.read_own", "teacher_attendance.write_own",
            "materials.read_own", "materials.write_own", "documents.read_own",
            "assignments.read_own", "assignments.write_own", "submissions.read_own", "submissions.write_own",
            "syllabus.read", "syllabus.write_own", "lesson_plans.read_own", "lesson_plans.write_own",
            "exams.read_own", "exams.write_own", "questions.read", "questions.write_own", "results.read_own", "results.write_own",
            "lms.read", "lms.write_own", "discussions.read_own", "discussions.write_own",
            "leaves.read_own", "leaves.write_own", "payroll.read_own", "hr.read_own",
            "announcements.read_own", "announcements.write_own", "messages.read_own", "messages.write_own",
            "meetings.read_own", "meetings.write_own", "surveys.read_own", "surveys.write_own",
            "notifications.read_own", "reports.read_own", "library.read_own", "ai.read_own", "ai.write_own",
        },
    },
    "student": {
        "name": "Student",
        "portal": "student",
        "permissions": {
            "courses.read", "subjects.read", "batches.read_own", "academic_years.read", "students.read_own",
            "enrollments.read_own", "schedules.read_own", "sessions.read_own", "attendance.read_own",
            "materials.read_own", "assignments.read_own", "submissions.read_own", "submissions.write_own",
            "syllabus.read", "exams.read_own", "results.read_own", "lms.read", "discussions.read_own",
            "discussions.write_own", "invoices.read_own", "payments.read_own", "fees.read_own",
            "announcements.read_own", "messages.read_own", "messages.write_own", "surveys.read_own", "surveys.write_own",
            "notifications.read_own", "library.read_own", "ai.read_own", "ai.write_own",
        },
    },
    "parent": {
        "name": "Parent / guardian",
        "portal": "parent",
        "permissions": {
            "courses.read", "subjects.read", "batches.read_own", "academic_years.read", "students.read_own",
            "parents.read_own", "enrollments.read_own", "schedules.read_own", "sessions.read_own", "attendance.read_own",
            "assignments.read_own", "submissions.read_own", "exams.read_own", "results.read_own", "syllabus.read",
            "invoices.read_own", "payments.read_own", "fees.read_own", "announcements.read_own", "messages.read_own",
            "messages.write_own", "meetings.read_own", "meetings.write_own", "surveys.read_own", "surveys.write_own",
            "notifications.read_own", "lms.read",
        },
    },
    "accountant": {
        "name": "Accountant",
        "portal": "admin",
        "permissions": _all(*_FINANCE) | {"students.read", "parents.read", "batches.read", "courses.read", "subjects.read",
                                          "reports.read", "invoices.adjust", "notifications.read_own", "imports.read",
                                          "branches.read", "academic_years.read", "sessions.read", "enrollments.read"},
    },
    "receptionist": {
        "name": "Receptionist",
        "portal": "admin",
        "permissions": _all("admissions", actions=("read", "write")) | {
            "students.read", "students.write", "parents.read", "parents.write", "courses.read", "batches.read",
            "subjects.read", "sessions.read", "schedules.read", "payments.read", "payments.write", "invoices.read",
            "announcements.read", "notifications.read_own", "branches.read", "academic_years.read", "enrollments.read",
            "enrollments.write", "documents.read", "documents.write",
        },
    },
    "academic_coordinator": {
        "name": "Academic coordinator",
        "portal": "admin",
        "permissions": _all(*_ACADEMIC) | {"students.read", "teachers.read", "parents.read", "reports.read",
                                           "announcements.read", "announcements.write", "attendance.reopen",
                                           "attendance.correct_approve", "results.approve", "grades.modify",
                                           "notifications.read_own", "branches.read", "leaves.read", "imports.read",
                                           "imports.write"},
    },
    "librarian": {
        "name": "Librarian",
        "portal": "admin",
        "permissions": _all("library") | {"students.read", "teachers.read", "notifications.read_own", "branches.read"},
    },
    "hr_manager": {
        "name": "HR manager",
        "portal": "admin",
        "permissions": _all("teachers", "leaves", "hr", "payroll") | {"teachers.contact", "payroll.approve", "reports.read",
                                                                       "teacher_attendance.read", "sessions.read",
                                                                       "notifications.read_own", "branches.read",
                                                                       "documents.read", "documents.write"},
    },
    "counsellor": {
        "name": "Counsellor",
        "portal": "admin",
        "permissions": _all("counselling", "admissions") | {"counselling.restricted", "admissions.counselling",
                                                            "students.read", "parents.read", "notifications.read_own",
                                                            "branches.read", "courses.read", "batches.read"},
    },
}
