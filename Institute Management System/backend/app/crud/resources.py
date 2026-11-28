"""Registration of every generic resource exposed under /api/v1/<name>."""

from datetime import date

from sqlalchemy import and_, func, or_, select, true

from app.core.errors import Conflict, ValidationFailed
from app.crud.engine import Resource, enrolled_students_subquery, register
from app.models import (
    AcademicYear,
    AdmissionRecord,
    AiRequest,
    Announcement,
    Asset,
    AssetAssignment,
    Assignment,
    AssignmentGrade,
    AssignmentTarget,
    AttendanceAuditLog,
    AttendanceCorrection,
    AuditLog,
    BackgroundJob,
    BankTransaction,
    Batch,
    BatchSubject,
    BillableCharge,
    Book,
    BookLoan,
    Branch,
    Budget,
    Campaign,
    CashbookEntry,
    ClassSchedule,
    ClassScheduleException,
    ClassSession,
    ClassSessionTeacher,
    Classroom,
    CompensationRule,
    CounsellingRecord,
    Course,
    CourseCompletion,
    CreditNote,
    CustomFieldDefinition,
    DemoClass,
    DiscussionThread,
    Document,
    EmploymentRecord,
    Enquiry,
    EnrollmentSubject,
    ExamAttempt,
    ExamQuestion,
    ExamResult,
    Examination,
    Expense,
    ExpenseCategory,
    FeePlan,
    FeePlanItem,
    FileDownloadLog,
    FinancialYear,
    FollowUp,
    GradeScale,
    Holiday,
    InventoryItem,
    InventoryTransaction,
    Invoice,
    InvoiceItem,
    Lead,
    LeaveBalance,
    LedgerEntry,
    LessonPlan,
    LessonProgress,
    LibraryMember,
    LmsLesson,
    LmsModule,
    MaintenanceRecord,
    Material,
    MaterialAccess,
    MaterialVersion,
    NotificationDelivery,
    NotificationTemplate,
    OnlineMeeting,
    Parent,
    ParentConsent,
    ParentMeeting,
    Payment,
    PaymentAllocation,
    PayrollPeriod,
    Payslip,
    PerformanceReview,
    PurchaseRecord,
    Question,
    ReEvaluationRequest,
    Refund,
    Student,
    StudentAttendance,
    StudentEnrollment,
    StudentFeeAgreement,
    StudentParent,
    Subject,
    Submission,
    Survey,
    SurveyResponse,
    SyllabusChapter,
    SyllabusProgress,
    TaxRate,
    Teacher,
    TeacherAssignment,
    TeacherAttendance,
    TeacherAvailability,
    TeacherLeave,
    TeacherPayableEntry,
    TeacherPayout,
    TenantSubscription,
    UsageRecord,
    Vendor,
    WebhookDelivery,
    WebhookEndpoint,
)
from app.services import numbering, scheduling

# ----------------------------------------------------------------------------- hooks


def _student_validate(db, p, obj, values, is_new):
    if is_new and not obj.student_code:
        obj.student_code = numbering.next_code(db, p.institute_id, "student", "STU")
    if is_new and not obj.admission_date:
        obj.admission_date = date.today()


def _teacher_validate(db, p, obj, values, is_new):
    if is_new and not obj.teacher_code:
        obj.teacher_code = numbering.next_code(db, p.institute_id, "teacher", "TCH")


def _enrollment_validate(db, p, obj, values, is_new):
    batch = db.get(Batch, obj.batch_id)
    if batch is None:
        raise ValidationFailed("Batch not found")
    obj.course_id = batch.course_id
    obj.academic_year_id = batch.academic_year_id
    obj.branch_id = batch.branch_id
    if obj.end_date and obj.end_date < obj.start_date:
        raise ValidationFailed("Enrollment end date must be on or after start date")
    if obj.status == "active" and (is_new or "status" in values or "batch_id" in values):
        active = db.scalar(
            select(func.count()).where(
                StudentEnrollment.batch_id == batch.id,
                StudentEnrollment.status == "active",
                StudentEnrollment.id != obj.id if obj.id else true(),
            )
        )
        if batch.capacity and active >= batch.capacity:
            raise Conflict(f"Batch {batch.name} is at full capacity ({batch.capacity})")


def _schedule_validate(db, p, obj, values, is_new):
    batch = db.get(Batch, obj.batch_id)
    if batch is None:
        raise ValidationFailed("Batch not found")
    obj.branch_id = batch.branch_id
    if not obj.academic_year_id:
        obj.academic_year_id = batch.academic_year_id
    if obj.classroom_id is None and batch.default_classroom_id:
        obj.classroom_id = batch.default_classroom_id
    if obj.end_time <= obj.start_time:
        raise ValidationFailed("End time must be after start time")
    conflicts = scheduling.schedule_conflicts(db, obj)
    scheduling.enforce_no_conflict(conflicts, obj.conflict_override_reason, p.can("schedules.override_conflict"))


def _enquiry_validate(db, p, obj, values, is_new):
    lead = db.get(Lead, obj.lead_id)
    if lead:
        obj.contact_name = lead.full_name
        obj.branch_id = obj.branch_id or lead.branch_id


def _expense_validate(db, p, obj, values, is_new):
    from app.services.finance import ensure_period_open

    ensure_period_open(db, p.institute_id, obj.expense_date)
    if is_new:
        obj.status = "submitted" if obj.status not in ("draft", "submitted") else obj.status


def _leave_validate(db, p, obj, values, is_new):
    if obj.end_date < obj.start_date:
        raise ValidationFailed("Leave end date must be on or after start date")
    obj.days = (obj.end_date - obj.start_date).days + 1
    if p.teacher_id and not p.can("leaves.write"):
        obj.teacher_id = p.teacher_id
        teacher = db.get(Teacher, p.teacher_id)
        obj.branch_id = teacher.branch_id
        if not is_new and obj.status != "pending":
            raise Conflict("Only pending leave requests can be changed")


def _inventory_txn_after(db, p, obj, is_new):
    if not is_new:
        return
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == obj.item_id).with_for_update())
    sign = -1 if obj.txn_type in ("issue", "damage") else 1
    new_qty = item.quantity_on_hand + sign * obj.quantity
    if new_qty < 0:
        raise ValidationFailed(f"Insufficient stock for {item.name} (on hand {item.quantity_on_hand})")
    item.quantity_on_hand = new_qty


def _payable_validate(db, p, obj, values, is_new):
    if is_new and obj.entry_type in ("salary", "per_class", "per_hour"):
        raise ValidationFailed("Salary and per-class entries are generated by payroll processing; add bonus/allowance/adjustment/deduction manually")


def _material_validate(db, p, obj, values, is_new):
    if obj.batch_id and not obj.course_id:
        b = db.get(Batch, obj.batch_id)
        obj.course_id = b.course_id if b else None
        obj.academic_year_id = obj.academic_year_id or (b.academic_year_id if b else None)


# ----------------------------------------------------------------------------- custom ownership filters


def _batches_own(p, M):
    return M.id.in_(p.batch_ids) if p.batch_ids else None


def _teacher_self(p, M):
    return M.id == p.teacher_id if p.teacher_id else None


def _parents_own(p, M):
    conds = []
    if p.parent_id:
        conds.append(M.id == p.parent_id)
    if p.teacher_id and p.batch_ids:
        conds.append(M.id.in_(select(StudentParent.parent_id).where(StudentParent.student_id.in_(enrolled_students_subquery(p.batch_ids)))))
    return or_(*conds) if conds else None


def _sessions_own(p, M):
    conds = []
    if p.teacher_id:
        conds.append(M.scheduled_teacher_id == p.teacher_id)
        conds.append(M.id.in_(select(ClassSessionTeacher.session_id).where(ClassSessionTeacher.teacher_id == p.teacher_id)))
    if p.batch_ids:
        conds.append(M.batch_id.in_(p.batch_ids))
    return or_(*conds) if conds else None


def _teacher_sessions_subq(p):
    return select(ClassSession.id).where(
        or_(
            ClassSession.scheduled_teacher_id == p.teacher_id,
            ClassSession.batch_id.in_(p.batch_ids) if p.batch_ids else False,
        )
    )


def _attendance_own(p, M):
    conds = []
    if p.linked_student_ids:
        conds.append(M.student_id.in_(p.linked_student_ids))
    if p.teacher_id:
        conds.append(M.session_id.in_(_teacher_sessions_subq(p)))
    return or_(*conds) if conds else None


def _materials_own(p, M):
    conds = []
    if p.teacher_id:
        conds.append(M.created_by_id == p.user_id)
        if p.batch_ids:
            conds.append(M.batch_id.in_(p.batch_ids))
    if p.linked_student_ids:
        granted = select(MaterialAccess.material_id).where(
            or_(
                MaterialAccess.student_id.in_(p.linked_student_ids),
                MaterialAccess.batch_id.in_(p.batch_ids) if p.batch_ids else False,
            )
        )
        conds.append(
            and_(
                M.visibility != "staff_only",
                or_(
                    M.visibility == "institute",
                    and_(M.visibility == "batch", M.batch_id.in_(p.batch_ids)) if p.batch_ids else False,
                    and_(M.visibility == "selected", M.id.in_(granted)),
                ),
            )
        )
    return or_(*conds) if conds else None


def _assignments_own(p, M):
    conds = []
    if p.teacher_id:
        conds.append(M.teacher_id == p.teacher_id)
        if p.batch_ids:
            conds.append(M.batch_id.in_(p.batch_ids))
    if p.linked_student_ids:
        targeted = select(AssignmentTarget.assignment_id).where(
            or_(
                AssignmentTarget.student_id.in_(p.linked_student_ids),
                AssignmentTarget.batch_id.in_(p.batch_ids) if p.batch_ids else False,
            )
        )
        conds.append(and_(M.status != "draft", M.id.in_(targeted)))
    return or_(*conds) if conds else None


def _submissions_own(p, M):
    conds = []
    if p.linked_student_ids:
        conds.append(M.student_id.in_(p.linked_student_ids))
    if p.teacher_id:
        conds.append(M.assignment_id.in_(select(Assignment.id).where(
            or_(Assignment.teacher_id == p.teacher_id, Assignment.batch_id.in_(p.batch_ids) if p.batch_ids else False)
        )))
    return or_(*conds) if conds else None


def _exam_child_own(p, M):
    conds = []
    if getattr(M, "student_id", None) is not None and p.linked_student_ids:
        conds.append(M.student_id.in_(p.linked_student_ids))
    if p.teacher_id and p.batch_ids:
        conds.append(M.examination_id.in_(select(Examination.id).where(Examination.batch_id.in_(p.batch_ids))))
    return or_(*conds) if conds else None


def _results_scope(p, M):
    # Students and parents only see published results.
    if p.is_staff or p.teacher_id:
        return None
    return M.status == "published"


def _exams_scope(p, M):
    if p.is_staff or p.teacher_id:
        return None
    return M.status != "draft"


def _counselling_scope(p, M):
    return None if p.can("counselling.restricted") else M.is_confidential.is_(False)


def _announcements_own(p, M):
    audiences = ["all"]
    if p.teacher_id:
        audiences += ["staff", "teachers"]
    if p.student_id:
        audiences.append("students")
    if p.parent_id:
        audiences.append("parents")
    visible = and_(
        M.status == "published",
        or_(M.expires_at.is_(None), M.expires_at > func.now()),
        or_(M.audience.in_(audiences), and_(M.audience == "batch", M.batch_id.in_(p.batch_ids)) if p.batch_ids else False),
    )
    if p.teacher_id:
        return or_(visible, M.created_by_id == p.user_id)
    return visible


def _surveys_own(p, M):
    audiences = ["all"]
    if p.teacher_id:
        audiences.append("teachers")
    if p.student_id:
        audiences.append("students")
    if p.parent_id:
        audiences.append("parents")
    visible = and_(M.status == "open", or_(M.audience.in_(audiences), and_(M.audience == "batch", M.batch_id.in_(p.batch_ids)) if p.batch_ids else False))
    if p.teacher_id:
        return or_(visible, M.created_by_id == p.user_id)
    return visible


def _invoice_children_own(p, M):
    if not p.linked_student_ids:
        return None
    return M.invoice_id.in_(select(Invoice.id).where(Invoice.student_id.in_(p.linked_student_ids)))


def _enrollment_subject_own(p, M):
    conds = []
    if p.linked_student_ids:
        conds.append(StudentEnrollment.student_id.in_(p.linked_student_ids))
    if p.batch_ids:
        conds.append(StudentEnrollment.batch_id.in_(p.batch_ids))
    if not conds:
        return None
    return M.enrollment_id.in_(select(StudentEnrollment.id).where(or_(*conds)))


def _lesson_progress_own(p, M):
    if p.linked_student_ids:
        return M.student_id.in_(p.linked_student_ids)
    return None


def _discussion_own(p, M):
    conds = [M.author_id == p.user_id]
    if p.batch_ids:
        conds.append(M.batch_id.in_(p.batch_ids))
    conds.append(M.batch_id.is_(None))
    return or_(*conds)


def _not_hidden_for_students(p, M):
    if p.is_staff or p.teacher_id:
        return None
    return M.is_hidden.is_(False)


def _published_lms(p, M):
    if p.is_staff or p.teacher_id:
        return None
    return M.is_published.is_(True)


# ----------------------------------------------------------------------------- registrations

R = register
ORG, PEOPLE, ACAD, CLASS, LEARN, EXAM, CRM, FIN, ACC, PAY, HR, COMM, RES, PLAT = (
    "Organisation", "People", "Academics", "Class operations", "Learning", "Examinations", "Admissions",
    "Fees & billing", "Accounting", "Payroll", "HR", "Communication", "Resources", "Platform",
)

R(Resource("branches", Branch, "branches", "Branches", ORG, search=("name", "code", "city"), list_columns=("name", "code", "city", "is_active")))
R(Resource("academic-years", AcademicYear, "academic_years", "Academic years", ORG, default_sort="-start_date",
           list_columns=("name", "start_date", "end_date", "status", "is_current")))
R(Resource("classrooms", Classroom, "classrooms", "Classrooms", ORG, search=("name", "code"), list_columns=("name", "code", "capacity", "branch_id", "is_active")))
R(Resource("holidays", Holiday, "schedules", "Holidays", ORG, search=("name",), default_sort="holiday_date",
           list_columns=("holiday_date", "name", "branch_id", "applies_to_classes")))
R(Resource("courses", Course, "courses", "Courses", ACAD, search=("name", "code"), list_columns=("name", "code", "duration_months", "is_active")))
R(Resource("subjects", Subject, "subjects", "Subjects", ACAD, search=("name", "code"), list_columns=("name", "code", "course_id", "is_active")))
R(Resource("batches", Batch, "batches", "Batches", ACAD, search=("name", "code"), own_filter=_batches_own,
           list_columns=("name", "code", "course_id", "academic_year_id", "capacity", "status")))
R(Resource("batch-subjects", BatchSubject, "batches", "Batch subjects", ACAD, owner={"batch": "batch_id"}, title_field="batch_id",
           list_columns=("batch_id", "subject_id", "weekly_hours", "is_active")))

R(Resource("students", Student, "students", "Students", PEOPLE, title_field="full_name",
           search=("full_name", "student_code", "phone", "email", "guardian_name", "guardian_phone"),
           owner={"student": "id"}, auto_fields=("student_code", "admission_date"), readonly=("user_id", "photo_object_key"),
           delete_perm="students.archive", validate=_student_validate,
           list_columns=("student_code", "full_name", "phone", "branch_id", "status", "admission_date")))
R(Resource("teachers", Teacher, "teachers", "Teachers", PEOPLE, title_field="full_name",
           search=("full_name", "teacher_code", "specialization"), own_filter=_teacher_self,
           auto_fields=("teacher_code",), readonly=("user_id", "photo_object_key"), validate=_teacher_validate,
           list_columns=("teacher_code", "full_name", "specialization", "employment_status", "compensation_type")))
R(Resource("parents", Parent, "parents", "Parents & guardians", PEOPLE, title_field="full_name", search=("full_name", "phone", "email"),
           own_filter=_parents_own, readonly=("user_id",), feature=None, list_columns=("full_name", "phone", "email", "is_active")))
R(Resource("student-parents", StudentParent, "parents", "Student–parent links", PEOPLE, owner={"student": "student_id"},
           title_field="relation", list_columns=("student_id", "parent_id", "relation", "is_primary")))
R(Resource("counselling-records", CounsellingRecord, "counselling", "Counselling & disciplinary", PEOPLE, title_field="record_type",
           scope_filter=_counselling_scope, default_sort="-record_date",
           list_columns=("record_date", "student_id", "record_type", "is_confidential")))

R(Resource("enrollments", StudentEnrollment, "enrollments", "Enrollments", ACAD, title_field="status",
           owner={"student": "student_id", "batch": "batch_id", "student_via_batch": "no"},
           auto_fields=("course_id", "academic_year_id"), readonly=("transferred_from_id",), validate=_enrollment_validate,
           list_columns=("student_id", "batch_id", "course_id", "start_date", "end_date", "status")))
R(Resource("enrollment-subjects", EnrollmentSubject, "enrollments", "Enrollment subjects", ACAD, own_filter=_enrollment_subject_own,
           title_field="start_date", list_columns=("enrollment_id", "subject_id", "start_date", "end_date")))
R(Resource("teacher-assignments", TeacherAssignment, "teacher_assignments", "Teacher assignments", ACAD, owner={"teacher": "teacher_id"},
           title_field="role", list_columns=("teacher_id", "batch_id", "subject_id", "role", "start_date", "end_date", "is_active")))
R(Resource("teacher-availability", TeacherAvailability, "teachers", "Teacher availability", HR, owner={"teacher": "teacher_id"},
           title_field="day_of_week", list_columns=("teacher_id", "day_of_week", "start_time", "end_time")))
R(Resource("schedules", ClassSchedule, "schedules", "Timetable schedules", CLASS, title_field="title",
           owner={"teacher": "teacher_id", "batch": "batch_id"}, auto_fields=("academic_year_id",), validate=_schedule_validate,
           default_sort="day_of_week,start_time",
           list_columns=("batch_id", "subject_id", "teacher_id", "day_of_week", "start_time", "end_time", "classroom_id", "is_active")))
R(Resource("schedule-exceptions", ClassScheduleException, "schedules", "Schedule exceptions", CLASS, title_field="action",
           default_sort="-exception_date", list_columns=("schedule_id", "exception_date", "action", "reason")))
R(Resource("class-sessions", ClassSession, "sessions", "Class sessions", CLASS, title_field="session_date", own_filter=_sessions_own,
           allow_create=False, allow_update=False, allow_delete=False, default_sort="-scheduled_start",
           list_columns=("session_date", "batch_id", "subject_id", "scheduled_teacher_id", "status", "attendance_state", "session_type")))
R(Resource("class-session-teachers", ClassSessionTeacher, "sessions", "Session teachers", CLASS, title_field="role",
           owner={"teacher": "teacher_id"}, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("student-attendance", StudentAttendance, "attendance", "Student attendance", CLASS, feature="attendance",
           title_field="status", own_filter=_attendance_own, allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("session_id", "student_id", "status", "remarks", "marked_at")))
R(Resource("teacher-attendance", TeacherAttendance, "teacher_attendance", "Teacher attendance", CLASS, feature="attendance",
           title_field="status", owner={"teacher": "teacher_id"}, allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("session_id", "teacher_id", "role", "status", "teaching_minutes", "is_verified")))
R(Resource("attendance-corrections", AttendanceCorrection, "attendance", "Attendance corrections", CLASS, feature="attendance",
           title_field="status", own_filter=_attendance_own, allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("session_id", "student_id", "original_status", "requested_status", "status", "created_at")))
R(Resource("attendance-audit-logs", AttendanceAuditLog, "attendance", "Attendance audit log", CLASS, feature="attendance",
           title_field="action", allow_create=False, allow_update=False, allow_delete=False))

R(Resource("materials", Material, "materials", "Study materials", LEARN, feature="materials", title_field="title",
           search=("title", "description", "tags"), own_filter=_materials_own, own_write=True,
           owner={"batch": "batch_id", "user": "created_by_id"}, readonly=("current_version",), allow_create=False,
           validate=_material_validate,
           list_columns=("title", "category", "batch_id", "subject_id", "visibility", "current_version", "created_at")))
R(Resource("material-versions", MaterialVersion, "materials", "Material versions", LEARN, feature="materials", title_field="original_filename",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("material-access", MaterialAccess, "materials", "Material access grants", LEARN, feature="materials", title_field="material_id",
           owner={"batch": "batch_id"}, own_write=True))
R(Resource("documents", Document, "documents", "Documents", LEARN, title_field="original_filename", search=("title", "original_filename"),
           allow_create=False, allow_update=True, readonly=("owner_type", "owner_id", "object_key", "mime_type", "size_bytes",
                                                            "checksum_sha256", "version_number", "previous_version_id", "original_filename"),
           list_columns=("title", "owner_type", "category", "original_filename", "version_number", "created_at")))
R(Resource("file-download-logs", FileDownloadLog, "audit", "File download log", PLAT, title_field="object_type",
           allow_create=False, allow_update=False, allow_delete=False))

R(Resource("assignments", Assignment, "assignments", "Homework & assignments", LEARN, feature="homework", title_field="title",
           search=("title",), own_filter=_assignments_own, own_write=True, owner={"teacher": "teacher_id", "batch": "batch_id"},
           readonly=("status", "published_at", "closed_at"), default_sort="-due_at",
           list_columns=("title", "batch_id", "subject_id", "teacher_id", "due_at", "status")))
R(Resource("assignment-targets", AssignmentTarget, "assignments", "Assignment targets", LEARN, feature="homework", title_field="assignment_id",
           allow_update=False, own_write=False))
R(Resource("submissions", Submission, "submissions", "Submissions", LEARN, feature="homework", title_field="status",
           own_filter=_submissions_own, allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("assignment_id", "student_id", "status", "submitted_at", "is_late")))
R(Resource("assignment-grades", AssignmentGrade, "submissions", "Assignment grades", LEARN, feature="homework", title_field="marks",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("syllabus-chapters", SyllabusChapter, "syllabus", "Syllabus chapters", ACAD, title_field="title", search=("title",),
           default_sort="sequence", list_columns=("title", "subject_id", "parent_id", "sequence", "planned_hours")))
R(Resource("syllabus-progress", SyllabusProgress, "syllabus", "Syllabus progress", ACAD, title_field="status",
           owner={"teacher": "teacher_id", "batch": "batch_id"}, own_write=True,
           list_columns=("batch_id", "chapter_id", "teacher_id", "planned_end", "status", "completed_date")))
R(Resource("lesson-plans", LessonPlan, "lesson_plans", "Lesson plans", ACAD, title_field="planned_date",
           owner={"teacher": "teacher_id", "batch": "batch_id"}, own_write=True, default_sort="-planned_date",
           list_columns=("planned_date", "teacher_id", "batch_id", "subject_id", "chapter_id", "status")))
R(Resource("lms-modules", LmsModule, "lms", "LMS modules", LEARN, feature="lms", title_field="title", scope_filter=_published_lms,
           default_sort="sequence", list_columns=("title", "course_id", "subject_id", "sequence", "is_published")))
R(Resource("lms-lessons", LmsLesson, "lms", "LMS lessons", LEARN, feature="lms", title_field="title", scope_filter=_published_lms,
           default_sort="sequence", list_columns=("title", "module_id", "lesson_type", "sequence", "is_published")))
R(Resource("lesson-progress", LessonProgress, "lms", "Learning progress", LEARN, feature="lms", title_field="status",
           own_filter=_lesson_progress_own, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("course-completions", CourseCompletion, "lms", "Course completions", LEARN, feature="lms", title_field="certificate_number",
           owner={"student": "student_id"}))
R(Resource("discussion-threads", DiscussionThread, "discussions", "Discussions & doubts", LEARN, feature="lms", title_field="title",
           search=("title", "body"), own_filter=_discussion_own, scope_filter=_not_hidden_for_students, allow_create=False,
           readonly=("author_id",), list_columns=("title", "batch_id", "subject_id", "is_doubt", "is_resolved", "created_at")))
R(Resource("online-meetings", OnlineMeeting, "lms", "Online meetings", LEARN, feature="lms", title_field="title", allow_create=False,
           readonly=("external_id", "provider"), list_columns=("title", "provider", "start_at", "status", "join_url")))

R(Resource("grade-scales", GradeScale, "exams", "Grade scales", EXAM, feature="examinations"))
R(Resource("examinations", Examination, "exams", "Examinations", EXAM, feature="examinations", search=("name", "term"),
           owner={"batch": "batch_id"}, own_write=True, scope_filter=_exams_scope,
           readonly=("status", "results_approved_by_id", "results_approved_at"), default_sort="-scheduled_start",
           list_columns=("name", "category", "batch_id", "subject_id", "mode", "scheduled_start", "status")))
R(Resource("questions", Question, "questions", "Question bank", EXAM, feature="examinations", title_field="question_text",
           search=("question_text", "tags"), owner={"user": "created_by_id"}, own_write=True,
           readonly=("is_ai_generated",), list_columns=("question_text", "subject_id", "question_type", "difficulty", "marks", "is_approved")))
R(Resource("exam-questions", ExamQuestion, "exams", "Exam questions", EXAM, feature="examinations", title_field="sequence",
           own_filter=_exam_child_own, default_sort="sequence"))
R(Resource("exam-results", ExamResult, "results", "Exam results", EXAM, feature="examinations", title_field="grade",
           own_filter=_exam_child_own, scope_filter=_results_scope, allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("examination_id", "student_id", "marks_obtained", "max_marks", "percentage", "grade", "rank", "status")))
R(Resource("exam-attempts", ExamAttempt, "exams", "Exam attempts", EXAM, feature="examinations", title_field="status",
           own_filter=_exam_child_own, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("re-evaluation-requests", ReEvaluationRequest, "results", "Re-evaluation requests", EXAM, feature="examinations",
           title_field="status", owner={"student": "student_id"}, allow_create=False, allow_update=False, allow_delete=False))

R(Resource("campaigns", Campaign, "admissions", "Campaigns", CRM, feature="admissions", search=("name",)))
R(Resource("leads", Lead, "admissions", "Leads", CRM, feature="admissions", title_field="full_name", search=("full_name", "phone", "email"),
           readonly=("student_id",), list_columns=("full_name", "phone", "source", "assigned_to_id", "created_at")))
R(Resource("enquiries", Enquiry, "admissions", "Enquiries", CRM, feature="admissions", title_field="contact_name",
           search=("contact_name", "interested_subjects"), readonly=("contact_name", "student_id", "converted_at"),
           validate=_enquiry_validate, default_sort="-created_at",
           list_columns=("contact_name", "course_id", "stage", "assigned_to_id", "next_follow_up_at")))
R(Resource("follow-ups", FollowUp, "admissions", "Follow-ups", CRM, feature="admissions", title_field="mode", default_sort="due_at",
           readonly=("reminder_sent_at",), list_columns=("enquiry_id", "due_at", "mode", "status", "assigned_to_id")))
R(Resource("demo-classes", DemoClass, "admissions", "Demo classes", CRM, feature="admissions", title_field="status",
           list_columns=("enquiry_id", "scheduled_at", "teacher_id", "subject_id", "status")))
R(Resource("admission-records", AdmissionRecord, "admissions", "Admission offers", CRM, feature="admissions", title_field="status",
           readonly=("student_id", "admission_fee_invoice_id", "admitted_at"),
           list_columns=("enquiry_id", "offer_date", "offered_batch_id", "offer_amount", "status")))

R(Resource("fee-plans", FeePlan, "fees", "Fee plans", FIN, feature="billing", search=("name", "code"),
           list_columns=("name", "code", "billing_type", "amount", "course_id", "is_active")))
R(Resource("fee-plan-items", FeePlanItem, "fees", "Fee plan items", FIN, feature="billing", default_sort="sequence"))
R(Resource("fee-agreements", StudentFeeAgreement, "fees", "Student fee agreements", FIN, feature="billing", title_field="billing_type",
           owner={"student": "student_id", "student_via_batch": "no"}, readonly=("approved_by_id",),
           list_columns=("student_id", "fee_plan_id", "billing_type", "amount", "effective_from", "effective_to", "status")))
R(Resource("invoices", Invoice, "invoices", "Invoices", FIN, feature="billing", title_field="invoice_number", search=("invoice_number",),
           owner={"student": "student_id", "student_via_batch": "no"}, allow_create=False, allow_update=False, allow_delete=False,
           default_sort="-issue_date",
           list_columns=("invoice_number", "student_id", "issue_date", "due_date", "total", "balance_due", "status")))
R(Resource("invoice-items", InvoiceItem, "invoices", "Invoice items", FIN, feature="billing", title_field="description",
           own_filter=_invoice_children_own, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("billable-charges", BillableCharge, "invoices", "Per-class charges", FIN, feature="billing", title_field="charge_date",
           allow_create=False, allow_update=False, allow_delete=False, default_sort="-charge_date",
           list_columns=("student_id", "session_id", "charge_date", "amount", "attendance_status", "status")))
R(Resource("payments", Payment, "payments", "Payments", FIN, feature="billing", title_field="receipt_number",
           search=("receipt_number", "reference_number"), owner={"student": "student_id", "student_via_batch": "no"},
           allow_create=False, allow_update=False, allow_delete=False, default_sort="-paid_at",
           list_columns=("receipt_number", "student_id", "paid_at", "amount", "method", "status", "unallocated_amount")))
R(Resource("payment-allocations", PaymentAllocation, "payments", "Payment allocations", FIN, feature="billing", title_field="amount",
           own_filter=_invoice_children_own, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("refunds", Refund, "refunds", "Refunds", FIN, feature="billing", title_field="refund_number",
           allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("refund_number", "student_id", "payment_id", "amount", "status", "created_at")))
R(Resource("credit-notes", CreditNote, "refunds", "Credit notes", FIN, feature="billing", title_field="credit_note_number",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("ledger-entries", LedgerEntry, "invoices", "Ledger", FIN, feature="billing", title_field="description",
           owner={"student": "student_id", "student_via_batch": "no"}, allow_create=False, allow_update=False, allow_delete=False,
           default_sort="-entry_date,-created_at"))

R(Resource("vendors", Vendor, "vendors", "Vendors", ACC, feature="accounting", search=("name", "contact_person", "phone")))
R(Resource("expense-categories", ExpenseCategory, "expenses", "Expense categories", ACC, feature="accounting"))
R(Resource("expenses", Expense, "expenses", "Expenses", ACC, feature="accounting", title_field="description", search=("description",),
           readonly=("approved_by_id", "approved_at", "paid_at"), validate=_expense_validate, default_sort="-expense_date",
           allow_delete=False, list_columns=("expense_date", "category_id", "vendor_id", "description", "amount", "status")))
R(Resource("purchase-records", PurchaseRecord, "vendors", "Purchases", ACC, feature="accounting", title_field="po_number",
           readonly=("approved_by_id", "approved_at", "expense_id"), default_sort="-purchase_date"))
R(Resource("cashbook-entries", CashbookEntry, "accounting", "Cashbook & petty cash", ACC, feature="accounting", title_field="description",
           default_sort="-entry_date", allow_delete=False))
R(Resource("bank-transactions", BankTransaction, "accounting", "Bank register", ACC, feature="accounting", title_field="description",
           default_sort="-txn_date", allow_delete=False))
R(Resource("budgets", Budget, "accounting", "Budgets", ACC, feature="accounting", title_field="amount"))
R(Resource("financial-years", FinancialYear, "accounting", "Financial years", ACC, feature="accounting",
           readonly=("status", "closed_at", "closed_by_id", "closing_summary"), allow_delete=False))
R(Resource("tax-rates", TaxRate, "accounting", "Tax rates", ACC, feature="accounting"))

R(Resource("compensation-rules", CompensationRule, "payroll", "Compensation rules", PAY, feature="teacher_compensation",
           title_field="compensation_type", owner={"teacher": "teacher_id"}))
R(Resource("payroll-periods", PayrollPeriod, "payroll", "Payroll periods", PAY, feature="teacher_compensation",
           readonly=("status", "approved_by_id", "approved_at"), default_sort="-start_date"))
R(Resource("teacher-payables", TeacherPayableEntry, "payroll", "Teacher payable entries", PAY, feature="teacher_compensation",
           title_field="description", owner={"teacher": "teacher_id"}, readonly=("status", "approved_by_id", "session_id", "rule_id"),
           validate=_payable_validate, default_sort="-entry_date",
           list_columns=("teacher_id", "entry_date", "entry_type", "description", "amount", "status")))
R(Resource("payslips", Payslip, "payroll", "Payslips", PAY, feature="teacher_compensation", title_field="payslip_number",
           owner={"teacher": "teacher_id"}, allow_create=False, allow_update=False, allow_delete=False))
R(Resource("teacher-payouts", TeacherPayout, "payroll", "Teacher payouts", PAY, feature="teacher_compensation", title_field="reference_number",
           owner={"teacher": "teacher_id"}, allow_create=False, allow_update=False, allow_delete=False))

R(Resource("teacher-leaves", TeacherLeave, "leaves", "Leave requests", HR, feature="hr_payroll", title_field="leave_type",
           owner={"teacher": "teacher_id"}, own_write=True, readonly=("status", "decided_by_id", "decided_at", "decision_remarks", "days"),
           validate=_leave_validate, default_sort="-start_date",
           list_columns=("teacher_id", "leave_type", "start_date", "end_date", "days", "status")))
R(Resource("leave-balances", LeaveBalance, "leaves", "Leave balances", HR, feature="hr_payroll", title_field="leave_type",
           owner={"teacher": "teacher_id"}))
R(Resource("employment-records", EmploymentRecord, "hr", "Employment records", HR, feature="hr_payroll", title_field="event_type",
           owner={"teacher": "teacher_id"}, default_sort="-effective_date"))
R(Resource("performance-reviews", PerformanceReview, "hr", "Performance reviews", HR, feature="hr_payroll", title_field="status",
           owner={"teacher": "teacher_id"}))

R(Resource("announcements", Announcement, "announcements", "Announcements", COMM, feature="communication", title_field="title",
           search=("title", "body"), own_filter=_announcements_own, own_write=True, owner={"batch": "batch_id", "user": "created_by_id"},
           readonly=("status", "published_at"), list_columns=("title", "audience", "priority", "status", "published_at")))
R(Resource("parent-meetings", ParentMeeting, "meetings", "Parent–teacher meetings", COMM, feature="communication", title_field="scheduled_at",
           owner={"student": "student_id", "teacher": "teacher_id", "student_via_batch": "no"}, own_write=True,
           list_columns=("scheduled_at", "parent_id", "teacher_id", "student_id", "mode", "status")))
R(Resource("surveys", Survey, "surveys", "Feedback & surveys", COMM, feature="communication", title_field="title",
           own_filter=_surveys_own, list_columns=("title", "survey_type", "audience", "status", "closes_at")))
R(Resource("survey-responses", SurveyResponse, "surveys", "Survey responses", COMM, feature="communication", title_field="survey_id",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("parent-consents", ParentConsent, "parents", "Parent consents", PEOPLE, title_field="consent_type",
           owner={"student": "student_id", "student_via_batch": "no"}))
R(Resource("notification-templates", NotificationTemplate, "notifications", "Notification templates", COMM, title_field="event_type"))
R(Resource("notification-deliveries", NotificationDelivery, "notifications", "Notification deliveries", COMM, title_field="channel",
           allow_create=False, allow_update=False, allow_delete=False, default_sort="-created_at",
           list_columns=("channel", "recipient", "status", "attempts", "last_error", "sent_at")))

R(Resource("books", Book, "library", "Library books", RES, feature="library", title_field="title", search=("title", "author", "isbn"),
           list_columns=("title", "author", "isbn", "copies_total", "copies_available", "shelf_location")))
R(Resource("library-members", LibraryMember, "library", "Library members", RES, feature="library", title_field="full_name",
           search=("full_name", "membership_number")))
R(Resource("book-loans", BookLoan, "library", "Book loans", RES, feature="library", title_field="issued_on", allow_create=False,
           readonly=("book_id", "member_id", "issued_on", "status", "returned_on", "reminder_sent_at"), allow_delete=False,
           list_columns=("book_id", "member_id", "issued_on", "due_date", "returned_on", "status", "fine_amount")))
R(Resource("inventory-items", InventoryItem, "inventory", "Inventory items", RES, feature="inventory", search=("name", "sku"),
           readonly=("quantity_on_hand",), list_columns=("name", "sku", "category", "quantity_on_hand", "reorder_level", "unit")))
R(Resource("inventory-transactions", InventoryTransaction, "inventory", "Stock movements", RES, feature="inventory",
           title_field="txn_type", allow_update=False, allow_delete=False, after_save=_inventory_txn_after, default_sort="-txn_date"))
R(Resource("assets", Asset, "assets", "Assets", RES, feature="inventory", search=("name", "asset_tag", "serial_number"),
           list_columns=("asset_tag", "name", "category", "classroom_id", "status")))
R(Resource("asset-assignments", AssetAssignment, "assets", "Asset assignments", RES, feature="inventory", title_field="assigned_on"))
R(Resource("maintenance-records", MaintenanceRecord, "assets", "Asset maintenance", RES, feature="inventory", title_field="maintenance_date"))

R(Resource("custom-fields", CustomFieldDefinition, "settings", "Custom fields", PLAT, title_field="label"))
R(Resource("webhook-endpoints", WebhookEndpoint, "webhooks", "Webhook endpoints", PLAT, title_field="url"))
R(Resource("webhook-deliveries", WebhookDelivery, "webhooks", "Webhook deliveries", PLAT, title_field="event_type",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("audit-logs", AuditLog, "audit", "Audit log", PLAT, title_field="action", search=("entity_type", "action", "actor_email"),
           allow_create=False, allow_update=False, allow_delete=False,
           list_columns=("created_at", "actor_email", "entity_type", "action", "reason")))
R(Resource("jobs", BackgroundJob, "imports", "Background jobs", PLAT, title_field="job_type", owner={"user": "created_by_id"},
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("ai-requests", AiRequest, "ai", "AI requests", PLAT, feature="ai", title_field="feature", owner={"user": "user_id"},
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("tenant-subscriptions", TenantSubscription, "saas", "Subscription", PLAT, feature="saas", title_field="status",
           allow_create=False, allow_update=False, allow_delete=False))
R(Resource("usage-records", UsageRecord, "saas", "Usage", PLAT, title_field="metric", allow_create=False, allow_update=False, allow_delete=False))
