from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    ArchiveMixin,
    Base,
    BranchEntity,
    OptBranchEntity,
    TenantEntity,
    bigint,
    boolean,
    date,
    decimal,
    enum,
    fk,
    integer,
    jsonb,
    string,
    text,
    ts,
    uuid_col,
)

MATERIAL_CATEGORIES = ("notes", "assignment", "question_paper", "answer_key", "reference", "student_submission", "other")


class Document(OptBranchEntity, ActorMixin, ArchiveMixin, Base):
    """Generic versioned document attached to any entity (student, teacher, admission, expense…)."""

    __tablename__ = "documents"
    owner_type = string(60, nullable=False)
    owner_id = uuid_col(nullable=False)
    category = string(60, nullable=False, default="other")
    title = string(255)
    original_filename = string(255, nullable=False)
    object_key = string(500, nullable=False, hidden=True)
    mime_type = string(120, nullable=False)
    size_bytes = bigint(nullable=False)
    checksum_sha256 = string(64, nullable=False)
    version_number = integer(nullable=False, default=1)
    previous_version_id = fk("documents.id")
    is_sensitive = boolean(False)
    __table_args__ = (UniqueConstraint("object_key"), Index("ix_documents_owner", "owner_type", "owner_id"))


class Material(OptBranchEntity, ActorMixin, ArchiveMixin, Base):
    __tablename__ = "materials"
    title = string(255, nullable=False)
    description = text()
    category = enum(*MATERIAL_CATEGORIES, default="notes")
    academic_year_id = fk("academic_years.id")
    course_id = fk("courses.id")
    batch_id = fk("batches.id")
    subject_id = fk("subjects.id")
    session_id = fk("class_sessions.id")
    syllabus_chapter_id = fk("syllabus_chapters.id")
    visibility = enum("staff_only", "batch", "selected", "institute", default="batch")
    current_version = integer(nullable=False, default=0)
    tags = string(500)


class MaterialVersion(TenantEntity, Base):
    __tablename__ = "material_versions"
    material_id = fk("materials.id", nullable=False)
    version_number = integer(nullable=False)
    original_filename = string(255, nullable=False)
    object_key = string(500, nullable=False, hidden=True)
    mime_type = string(120, nullable=False)
    size_bytes = bigint(nullable=False)
    checksum_sha256 = string(64, nullable=False)
    change_note = text()
    uploaded_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (UniqueConstraint("material_id", "version_number"), UniqueConstraint("object_key"))


class MaterialAccess(TenantEntity, Base):
    __tablename__ = "material_access"
    material_id = fk("materials.id", nullable=False, ondelete="CASCADE")
    batch_id = fk("batches.id")
    student_id = fk("students.id")
    granted_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (CheckConstraint("batch_id IS NOT NULL OR student_id IS NOT NULL", name="ck_material_access_target"),)


class FileDownloadLog(TenantEntity, Base):
    __tablename__ = "file_download_logs"
    user_id = fk("users.id", ondelete="SET NULL")
    object_type = string(60, nullable=False)
    object_id = uuid_col(nullable=False)
    version_id = uuid_col()
    ip_address = string(64)
    user_agent = string(500)


class Assignment(BranchEntity, ActorMixin, Base):
    __tablename__ = "assignments"
    title = string(255, nullable=False)
    description = text()
    instructions = text()
    academic_year_id = fk("academic_years.id")
    subject_id = fk("subjects.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    teacher_id = fk("teachers.id", nullable=False)
    session_id = fk("class_sessions.id")
    assigned_date = date(nullable=False)
    due_at = ts(nullable=False)
    max_marks = decimal(6, 2, nullable=False, default=100)
    submission_type = enum("file", "text", "file_or_text", "offline", default="file_or_text")
    allow_late = boolean(True)
    late_until = ts()
    late_penalty_percent = decimal(5, 2, nullable=False, default=0)
    allow_resubmission = boolean(False)
    target_type = enum("batch", "students", "multi_batch", default="batch")
    status = enum("draft", "published", "submission_open", "under_evaluation", "evaluated", "closed", default="draft")
    published_at = ts()
    closed_at = ts()
    __table_args__ = (
        CheckConstraint("max_marks >= 0", name="ck_assignments_marks"),
        CheckConstraint("late_penalty_percent BETWEEN 0 AND 100", name="ck_assignments_penalty"),
    )


class AssignmentTarget(TenantEntity, Base):
    __tablename__ = "assignment_targets"
    assignment_id = fk("assignments.id", nullable=False, ondelete="CASCADE")
    batch_id = fk("batches.id")
    student_id = fk("students.id")
    __table_args__ = (
        CheckConstraint("batch_id IS NOT NULL OR student_id IS NOT NULL", name="ck_assignment_targets"),
        UniqueConstraint("assignment_id", "batch_id", "student_id"),
    )


class AssignmentAttachment(TenantEntity, Base):
    __tablename__ = "assignment_attachments"
    assignment_id = fk("assignments.id", nullable=False)
    original_filename = string(255, nullable=False)
    object_key = string(500, nullable=False, hidden=True)
    mime_type = string(120, nullable=False)
    size_bytes = bigint(nullable=False)
    checksum_sha256 = string(64, nullable=False)
    uploaded_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (UniqueConstraint("object_key"),)


SUBMISSION_STATUSES = ("draft", "submitted", "late", "under_review", "evaluated", "resubmission_requested")


class Submission(TenantEntity, Base):
    __tablename__ = "submissions"
    assignment_id = fk("assignments.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    status = enum(*SUBMISSION_STATUSES, default="draft")
    current_version = integer(nullable=False, default=0)
    submitted_at = ts()
    is_late = boolean(False)
    remarks = text()
    __table_args__ = (UniqueConstraint("assignment_id", "student_id"),)


class SubmissionVersion(TenantEntity, Base):
    __tablename__ = "submission_versions"
    submission_id = fk("submissions.id", nullable=False)
    version_number = integer(nullable=False)
    text_content = text()
    remarks = text()
    is_final = boolean(False)
    submitted_at = ts()
    is_late = boolean(False)
    __table_args__ = (UniqueConstraint("submission_id", "version_number"),)


class SubmissionFile(TenantEntity, Base):
    __tablename__ = "submission_files"
    submission_version_id = fk("submission_versions.id", nullable=False)
    original_filename = string(255, nullable=False)
    object_key = string(500, nullable=False, hidden=True)
    mime_type = string(120, nullable=False)
    size_bytes = bigint(nullable=False)
    checksum_sha256 = string(64, nullable=False)
    __table_args__ = (UniqueConstraint("object_key"),)


class AssignmentGrade(TenantEntity, Base):
    __tablename__ = "assignment_grades"
    submission_id = fk("submissions.id", nullable=False)
    submission_version_id = fk("submission_versions.id")
    marks = decimal(6, 2, nullable=False)
    penalty_applied = decimal(6, 2, nullable=False, default=0)
    feedback = text()
    graded_by_id = fk("users.id", ondelete="SET NULL")
    is_current = boolean(True)
    modification_reason = text()
    __table_args__ = (
        CheckConstraint("marks >= 0", name="ck_grades_marks"),
        Index("uq_grade_current", "submission_id", unique=True, postgresql_where=sql_text("is_current")),
    )


class AssignmentComment(TenantEntity, Base):
    __tablename__ = "assignment_comments"
    assignment_id = fk("assignments.id", nullable=False)
    submission_id = fk("submissions.id")
    author_id = fk("users.id", ondelete="SET NULL")
    body = text(nullable=False)
    is_hidden = boolean(False)


class SyllabusChapter(TenantEntity, ActorMixin, Base):
    __tablename__ = "syllabus_chapters"
    course_id = fk("courses.id")
    subject_id = fk("subjects.id", nullable=False)
    parent_id = fk("syllabus_chapters.id", label="Parent chapter (for topics)")
    title = string(255, nullable=False)
    description = text()
    learning_outcomes = text()
    sequence = integer(nullable=False, default=1)
    planned_hours = decimal(6, 2)
    resource_notes = text()


class SyllabusProgress(BranchEntity, Base):
    __tablename__ = "syllabus_progress"
    batch_id = fk("batches.id", nullable=False)
    chapter_id = fk("syllabus_chapters.id", nullable=False)
    teacher_id = fk("teachers.id")
    planned_start = date()
    planned_end = date()
    status = enum("not_started", "in_progress", "completed", default="not_started")
    completed_date = date()
    last_session_id = fk("class_sessions.id")
    __table_args__ = (UniqueConstraint("batch_id", "chapter_id"),)


class LessonPlan(BranchEntity, ActorMixin, Base):
    __tablename__ = "lesson_plans"
    teacher_id = fk("teachers.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    subject_id = fk("subjects.id", nullable=False)
    chapter_id = fk("syllabus_chapters.id")
    session_id = fk("class_sessions.id")
    planned_date = date(nullable=False)
    objectives = text()
    activities = text()
    resources = text()
    status = enum("planned", "in_progress", "completed", "skipped", default="planned")
    completed_date = date()
    remarks = text()


# ----------------------------------------------------------------------------- LMS


class LmsModule(TenantEntity, ActorMixin, Base):
    __tablename__ = "lms_modules"
    course_id = fk("courses.id", nullable=False)
    subject_id = fk("subjects.id")
    title = string(255, nullable=False)
    description = text()
    sequence = integer(nullable=False, default=1)
    is_published = boolean(False)


class LmsLesson(TenantEntity, ActorMixin, Base):
    __tablename__ = "lms_lessons"
    module_id = fk("lms_modules.id", nullable=False)
    title = string(255, nullable=False)
    lesson_type = enum("text", "video", "link", "document", "quiz", "live", default="text")
    content = text(widget="textarea")
    video_url = string(500)
    resource_url = string(500)
    material_id = fk("materials.id")
    examination_id = fk("examinations.id", label="Practice quiz")
    duration_minutes = integer()
    sequence = integer(nullable=False, default=1)
    is_published = boolean(False)


class LessonProgress(TenantEntity, Base):
    __tablename__ = "lesson_progress"
    lesson_id = fk("lms_lessons.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    status = enum("not_started", "in_progress", "completed", default="not_started")
    progress_percent = integer(nullable=False, default=0)
    completed_at = ts()
    last_accessed_at = ts()
    __table_args__ = (
        UniqueConstraint("lesson_id", "student_id"),
        CheckConstraint("progress_percent BETWEEN 0 AND 100", name="ck_lesson_progress_pct"),
    )


class CourseCompletion(TenantEntity, ActorMixin, Base):
    __tablename__ = "course_completions"
    course_id = fk("courses.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    completed_on = date(nullable=False)
    certificate_number = string(60)
    remarks = text()
    __table_args__ = (UniqueConstraint("course_id", "student_id"),)


class DiscussionThread(TenantEntity, Base):
    __tablename__ = "discussion_threads"
    batch_id = fk("batches.id")
    subject_id = fk("subjects.id")
    lesson_id = fk("lms_lessons.id")
    title = string(255, nullable=False)
    body = text(nullable=False)
    author_id = fk("users.id", ondelete="SET NULL")
    is_doubt = boolean(False)
    is_resolved = boolean(False)
    is_locked = boolean(False)
    is_hidden = boolean(False)


class DiscussionPost(TenantEntity, Base):
    __tablename__ = "discussion_posts"
    thread_id = fk("discussion_threads.id", nullable=False)
    author_id = fk("users.id", ondelete="SET NULL")
    body = text(nullable=False)
    is_answer = boolean(False)
    is_hidden = boolean(False)
    report_count = integer(nullable=False, default=0)


class OnlineMeeting(TenantEntity, ActorMixin, Base):
    __tablename__ = "online_meetings"
    session_id = fk("class_sessions.id")
    provider = enum("manual", "zoom", "google_meet", default="manual")
    title = string(255, nullable=False)
    join_url = string(1000)
    host_url = string(1000, sensitive="lms.manage")
    external_id = string(255)
    start_at = ts(nullable=False)
    duration_minutes = integer(nullable=False, default=60)
    status = enum("scheduled", "live", "ended", "cancelled", "failed", default="scheduled")
    recording_url = string(1000)
    provider_payload = jsonb(hidden=True)
