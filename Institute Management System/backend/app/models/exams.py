from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.base import (
    ActorMixin,
    ArchiveMixin,
    Base,
    BranchEntity,
    TenantEntity,
    boolean,
    decimal,
    enum,
    fk,
    integer,
    jsonb,
    string,
    text,
    ts,
)

QUESTION_TYPES = ("mcq_single", "mcq_multi", "true_false", "numerical", "fill_blank", "descriptive")


class GradeScale(TenantEntity, ActorMixin, Base):
    __tablename__ = "grade_scales"
    name = string(120, nullable=False)
    bands = jsonb("list", label='Bands JSON: [{"min":90,"max":100,"grade":"A+","point":10}]')
    is_default = boolean(False)


class Examination(BranchEntity, ActorMixin, Base):
    __tablename__ = "examinations"
    name = string(255, nullable=False)
    category = enum("unit_test", "mid_term", "final", "mock", "quiz", "practice", "entrance", default="unit_test")
    term = string(60)
    academic_year_id = fk("academic_years.id")
    course_id = fk("courses.id")
    batch_id = fk("batches.id", nullable=False)
    subject_id = fk("subjects.id", nullable=False)
    mode = enum("online", "offline", default="offline")
    scheduled_start = ts()
    scheduled_end = ts()
    duration_minutes = integer()
    max_marks = decimal(7, 2, nullable=False, default=100)
    pass_marks = decimal(7, 2)
    negative_marking = boolean(False)
    randomize_questions = boolean(False)
    randomize_options = boolean(False)
    grade_scale_id = fk("grade_scales.id")
    instructions = text()
    status = enum("draft", "scheduled", "live", "completed", "results_published", "cancelled", default="draft")
    results_approved_by_id = fk("users.id", ondelete="SET NULL")
    results_approved_at = ts()
    __table_args__ = (CheckConstraint("max_marks > 0", name="ck_exams_max_marks"),)


class Question(TenantEntity, ActorMixin, ArchiveMixin, Base):
    __tablename__ = "questions"
    subject_id = fk("subjects.id", nullable=False)
    chapter_id = fk("syllabus_chapters.id")
    question_type = enum(*QUESTION_TYPES, default="mcq_single")
    difficulty = enum("easy", "medium", "hard", default="medium")
    question_text = text(nullable=False, widget="textarea")
    options = jsonb("list", label='Options JSON: [{"key":"A","text":"..."}]')
    correct_answer = jsonb("list", staff_only=True, label='Correct answer JSON, e.g. ["A"] or [42.5]')
    numeric_tolerance = decimal(10, 4)
    marks = decimal(6, 2, nullable=False, default=1)
    negative_marks = decimal(6, 2, nullable=False, default=0)
    explanation = text()
    tags = string(500)
    is_ai_generated = boolean(False)
    is_approved = boolean(True)


class ExamQuestion(TenantEntity, Base):
    __tablename__ = "exam_questions"
    examination_id = fk("examinations.id", nullable=False, ondelete="CASCADE")
    question_id = fk("questions.id", nullable=False)
    sequence = integer(nullable=False, default=1)
    marks = decimal(6, 2)
    negative_marks = decimal(6, 2)
    __table_args__ = (UniqueConstraint("examination_id", "question_id"),)


class ExamAttempt(TenantEntity, Base):
    __tablename__ = "exam_attempts"
    examination_id = fk("examinations.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    started_at = ts(nullable=False)
    deadline_at = ts(nullable=False)
    submitted_at = ts()
    status = enum("in_progress", "submitted", "auto_submitted", "graded", default="in_progress")
    question_order = jsonb("list", hidden=True)
    option_order = jsonb(hidden=True)
    objective_score = decimal(8, 2)
    __table_args__ = (UniqueConstraint("examination_id", "student_id"),)


class ExamResponse(TenantEntity, Base):
    __tablename__ = "exam_responses"
    attempt_id = fk("exam_attempts.id", nullable=False, ondelete="CASCADE")
    question_id = fk("questions.id", nullable=False)
    answer = jsonb("list")
    is_correct = boolean(False)
    needs_manual_grading = boolean(False)
    marks_awarded = decimal(6, 2)
    graded_by_id = fk("users.id", ondelete="SET NULL")
    feedback = text()
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)


class ExamResult(TenantEntity, ActorMixin, Base):
    __tablename__ = "exam_results"
    examination_id = fk("examinations.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    marks_obtained = decimal(7, 2)
    max_marks = decimal(7, 2, nullable=False)
    percentage = decimal(5, 2)
    grade = string(10)
    rank = integer()
    is_absent = boolean(False)
    remarks = text()
    remedial_recommendation = text()
    status = enum("draft", "approved", "published", default="draft")
    approved_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (
        UniqueConstraint("examination_id", "student_id"),
        CheckConstraint("marks_obtained IS NULL OR marks_obtained >= 0", name="ck_results_marks"),
    )


class ReEvaluationRequest(TenantEntity, Base):
    __tablename__ = "re_evaluation_requests"
    exam_result_id = fk("exam_results.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    reason = text(nullable=False)
    status = enum("pending", "accepted", "rejected", "completed", default="pending")
    old_marks = decimal(7, 2)
    new_marks = decimal(7, 2)
    reviewer_id = fk("users.id", ondelete="SET NULL")
    reviewed_at = ts()
    remarks = text()
    requested_by_id = fk("users.id", ondelete="SET NULL")
