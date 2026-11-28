"""Dashboards and reports. Every query is tenant- and branch-scoped and reads persisted data only."""

import uuid
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Date, and_, case, cast, distinct, extract, func, or_, select, true
from sqlalchemy.orm import Session

from app.api.common import file_response
from app.api.deps import Principal, get_principal
from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.db.session import get_db
from app.models import (
    AcademicYear,
    Assignment,
    AssignmentGrade,
    AuditLog,
    Batch,
    BatchSubject,
    Branch,
    ClassSchedule,
    ClassSession,
    ClassSessionTeacher,
    Classroom,
    Course,
    Enquiry,
    ExamResult,
    Examination,
    Expense,
    ExpenseCategory,
    FeePlan,
    Invoice,
    InvoiceItem,
    Lead,
    Material,
    Payment,
    PayrollPeriod,
    Payslip,
    Refund,
    Student,
    StudentAttendance,
    StudentEnrollment,
    StudentFeeAgreement,
    Subject,
    Submission,
    SyllabusChapter,
    SyllabusProgress,
    Teacher,
    TeacherAttendance,
    TeacherAvailability,
    TeacherLeave,
    TeacherPayout,
)
from app.services import app_settings, exporter, feature_flags, finance
from app.services.scheduling import institute_tz, today_local

router = APIRouter(tags=["Reports & dashboards"])

PRESENT = ("present", "late")


def bscope(p: Principal, col):
    """Branch scope condition for a branch_id column (respects branch-limited users and the branch selector)."""
    conds = []
    if p.branch_ids is not None:
        conds.append(col.in_(p.branch_ids))
    if p.selected_branch_id:
        conds.append(col == p.selected_branch_id)
    return and_(*conds) if conds else true()


def pct(a, b) -> float | None:
    return round(float(a) * 100 / float(b), 1) if b else None


def month_start(d: date, back: int = 0) -> date:
    y, m = d.year, d.month - back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def day_bounds(db: Session, p: Principal, d: date) -> tuple[datetime, datetime]:
    tz = institute_tz(db, p.institute_id)
    start = datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc)
    return start, start + timedelta(days=1)


# ----------------------------------------------------------------------------- admin dashboard


@router.get("/dashboard/admin")
def admin_dashboard(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if not p.is_staff:
        raise Forbidden("Administrator dashboard is for staff")
    I = p.institute_id
    today = today_local(db, I)
    flags = feature_flags.get_flags(db, I)
    m0 = month_start(today)
    d0, d1 = day_bounds(db, p, m0)
    att_today = dict(db.execute(select(StudentAttendance.status, func.count()).join(ClassSession, ClassSession.id == StudentAttendance.session_id)
                                .where(ClassSession.institute_id == I, ClassSession.session_date == today, bscope(p, ClassSession.branch_id))
                                .group_by(StudentAttendance.status)).all())
    t_att = dict(db.execute(select(TeacherAttendance.status, func.count()).join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
                            .where(ClassSession.institute_id == I, ClassSession.session_date == today, bscope(p, ClassSession.branch_id))
                            .group_by(TeacherAttendance.status)).all())
    sessions_today = db.scalars(select(ClassSession).where(ClassSession.institute_id == I, ClassSession.session_date == today,
                                                           bscope(p, ClassSession.branch_id)).order_by(ClassSession.scheduled_start)).all()
    from app.api.v1.classes import _labels, session_out

    L = _labels(db, list(sessions_today))
    can_fin = p.can("invoices.read") or p.can("payments.read")
    stats: dict[str, Any] = {
        "active_students": db.scalar(select(func.count()).where(Student.institute_id == I, Student.status == "active", Student.is_archived.is_(False),
                                                                bscope(p, Student.branch_id))),
        "active_teachers": db.scalar(select(func.count()).where(Teacher.institute_id == I, Teacher.employment_status == "active",
                                                                Teacher.is_archived.is_(False), bscope(p, Teacher.branch_id))),
        "active_batches": db.scalar(select(func.count()).where(Batch.institute_id == I, Batch.status == "active", bscope(p, Batch.branch_id))),
        "classes_today": sum(1 for s in sessions_today if s.status not in ("cancelled",)),
        "classes_completed_today": sum(1 for s in sessions_today if s.status == "completed"),
        "student_attendance_today": {"marked": sum(att_today.values()), "present": sum(att_today.get(k, 0) for k in PRESENT),
                                     "percentage": pct(sum(att_today.get(k, 0) for k in PRESENT), sum(att_today.values()))},
        "teacher_attendance_today": {"marked": sum(t_att.values()), "present": sum(t_att.get(k, 0) for k in PRESENT)},
        "upcoming_assignments": db.scalar(select(func.count()).where(Assignment.institute_id == I, Assignment.status == "submission_open",
                                                                     Assignment.due_at.between(datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=7)),
                                                                     bscope(p, Assignment.branch_id))),
        "pending_evaluations": db.scalar(select(func.count()).select_from(Submission).join(Assignment, Assignment.id == Submission.assignment_id)
                                         .where(Submission.institute_id == I, Submission.status.in_(("submitted", "late", "under_review")),
                                                bscope(p, Assignment.branch_id))),
    }
    if can_fin and flags.get("billing"):
        stats["monthly_collection"] = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.institute_id == I, Payment.status == "completed", Payment.paid_at >= d0, bscope(p, Payment.branch_id)))
        stats["outstanding_fees"] = db.scalar(select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(
            Invoice.institute_id == I, Invoice.status.in_(("issued", "partially_paid", "overdue")), bscope(p, Invoice.branch_id)))
    # charts
    att_trend, rev_trend = [], []
    for back in range(5, -1, -1):
        ms = month_start(today, back)
        me = month_start(today, back - 1) - timedelta(days=1) if back > 0 else today
        tot, pres = db.execute(select(func.count(), func.sum(case((StudentAttendance.status.in_(PRESENT), 1), else_=0)))
                               .join(ClassSession, ClassSession.id == StudentAttendance.session_id)
                               .where(ClassSession.institute_id == I, ClassSession.session_date.between(ms, me), bscope(p, ClassSession.branch_id))).one()
        att_trend.append({"month": ms.strftime("%b %Y"), "percentage": pct(pres or 0, tot)})
        if can_fin and flags.get("billing"):
            a, b = day_bounds(db, p, ms)[0], day_bounds(db, p, me)[1]
            rev_trend.append({"month": ms.strftime("%b %Y"), "amount": float(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.institute_id == I, Payment.status == "completed", Payment.paid_at.between(a, b), bscope(p, Payment.branch_id))) or 0)})
    last30 = today - timedelta(days=30)
    subj_att = [{"subject": n, "percentage": pct(pr or 0, t)} for n, t, pr in db.execute(
        select(Subject.name, func.count(), func.sum(case((StudentAttendance.status.in_(PRESENT), 1), else_=0)))
        .join(ClassSession, ClassSession.id == StudentAttendance.session_id).join(Subject, Subject.id == ClassSession.subject_id)
        .where(ClassSession.institute_id == I, ClassSession.session_date >= last30, bscope(p, ClassSession.branch_id)).group_by(Subject.name)).all()]
    strength = [{"batch": n, "students": c, "capacity": cap} for n, c, cap in db.execute(
        select(Batch.name, func.count(StudentEnrollment.id), Batch.capacity).outerjoin(
            StudentEnrollment, and_(StudentEnrollment.batch_id == Batch.id, StudentEnrollment.status == "active"))
        .where(Batch.institute_id == I, Batch.status == "active", bscope(p, Batch.branch_id)).group_by(Batch.id).order_by(Batch.name).limit(20)).all()]
    workload = [{"teacher": n, "sessions": c} for n, c in db.execute(
        select(Teacher.full_name, func.count(ClassSession.id)).join(ClassSession, ClassSession.scheduled_teacher_id == Teacher.id)
        .where(Teacher.institute_id == I, ClassSession.session_date.between(m0, today), ClassSession.status != "cancelled",
               bscope(p, ClassSession.branch_id)).group_by(Teacher.full_name).order_by(func.count(ClassSession.id).desc()).limit(15)).all()]
    charts: dict[str, Any] = {"attendance_trend": att_trend, "revenue_trend": rev_trend, "subject_attendance": subj_att, "batch_strength": strength,
                              "teacher_workload": workload}
    if flags.get("admissions") and p.can("admissions.read"):
        charts["admission_funnel"] = [{"stage": s, "count": c} for s, c in db.execute(
            select(Enquiry.stage, func.count()).where(Enquiry.institute_id == I, bscope(p, Enquiry.branch_id)).group_by(Enquiry.stage)).all()]
    threshold = app_settings.get(db, I, "attendance.alert_threshold_percent")
    attention = [{"student_id": sid, "full_name": n, "student_code": code, "percentage": pct(pr or 0, t), "sessions": t} for sid, n, code, t, pr in db.execute(
        select(Student.id, Student.full_name, Student.student_code, func.count(), func.sum(case((StudentAttendance.status.in_(PRESENT), 1), else_=0)))
        .join(StudentAttendance, StudentAttendance.student_id == Student.id).join(ClassSession, ClassSession.id == StudentAttendance.session_id)
        .where(Student.institute_id == I, ClassSession.session_date >= last30, Student.status == "active", bscope(p, Student.branch_id))
        .group_by(Student.id).having(func.count() >= 4)).all() if pct(pr or 0, t) is not None and pct(pr or 0, t) < threshold]
    sections: dict[str, Any] = {
        "todays_timetable": [session_out(s, L) for s in sessions_today],
        "students_needing_attention": sorted(attention, key=lambda r: r["percentage"])[:10],
        "recent_uploads": [{"id": m.id, "title": m.title, "category": m.category, "created_at": m.created_at} for m in db.scalars(
            select(Material).where(Material.institute_id == I, Material.is_archived.is_(False)).order_by(Material.created_at.desc()).limit(6))],
        "recent_activity": [{"at": a.created_at, "actor": a.actor_email, "action": a.action, "entity": a.entity_type} for a in db.scalars(
            select(AuditLog).where(AuditLog.institute_id == I).order_by(AuditLog.created_at.desc()).limit(10))] if p.can("audit.read") else [],
    }
    if can_fin and flags.get("billing"):
        sections["upcoming_fee_dues"] = [{"id": i.id, "invoice_number": i.invoice_number, "student": n, "due_date": i.due_date, "balance_due": i.balance_due}
                                         for i, n in db.execute(select(Invoice, Student.full_name).join(Student, Student.id == Invoice.student_id).where(
                                             Invoice.institute_id == I, Invoice.status.in_(("issued", "partially_paid")),
                                             Invoice.due_date.between(today, today + timedelta(days=14)), bscope(p, Invoice.branch_id))
                                             .order_by(Invoice.due_date).limit(10)).all()]
        sections["recent_transactions"] = [{"id": x.id, "receipt_number": x.receipt_number, "student": n, "amount": x.amount, "method": x.method,
                                            "paid_at": x.paid_at, "status": x.status}
                                           for x, n in db.execute(select(Payment, Student.full_name).join(Student, Student.id == Payment.student_id)
                                                                  .where(Payment.institute_id == I, bscope(p, Payment.branch_id))
                                                                  .order_by(Payment.paid_at.desc()).limit(10)).all()]
    onboarding = {
        "branches": db.scalar(select(func.count()).where(Branch.institute_id == I)) > 0,
        "academic_year": db.scalar(select(func.count()).where(AcademicYear.institute_id == I)) > 0,
        "courses": db.scalar(select(func.count()).where(Course.institute_id == I)) > 0,
        "subjects": db.scalar(select(func.count()).where(Subject.institute_id == I)) > 0,
        "batches": db.scalar(select(func.count()).where(Batch.institute_id == I)) > 0,
        "teachers": db.scalar(select(func.count()).where(Teacher.institute_id == I)) > 0,
        "students": db.scalar(select(func.count()).where(Student.institute_id == I)) > 0,
        "schedules": db.scalar(select(func.count()).where(ClassSchedule.institute_id == I)) > 0,
        "fee_plans": db.scalar(select(func.count()).where(FeePlan.institute_id == I)) > 0,
    }
    return {"date": today, "stats": stats, "charts": charts, "sections": sections, "onboarding": onboarding}


# ----------------------------------------------------------------------------- teacher dashboard


@router.get("/dashboard/teacher")
def teacher_dashboard(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if not p.teacher_id:
        raise Forbidden("Teacher dashboard requires a teacher profile")
    from app.api.v1.classes import _labels, session_out

    I, T = p.institute_id, p.teacher_id
    today = today_local(db, I)
    mine = or_(ClassSession.scheduled_teacher_id == T, ClassSession.id.in_(select(ClassSessionTeacher.session_id).where(ClassSessionTeacher.teacher_id == T)))
    upcoming = db.scalars(select(ClassSession).where(ClassSession.institute_id == I, mine, ClassSession.session_date.between(today, today + timedelta(days=7)),
                                                     ClassSession.status != "cancelled").order_by(ClassSession.scheduled_start).limit(40)).all()
    pending_att = db.scalars(select(ClassSession).where(ClassSession.institute_id == I, mine, ClassSession.session_date <= today,
                                                        ClassSession.session_date >= today - timedelta(days=14),
                                                        ClassSession.status.notin_(("cancelled", "postponed")),
                                                        ClassSession.attendance_state.in_(("not_started", "draft", "reopened"))).order_by(ClassSession.scheduled_start)).all()
    L = _labels(db, list(upcoming) + list(pending_att))
    assignments = db.execute(select(Batch.name, Subject.name, Batch.id).join(Batch, Batch.id == ClassSchedule.batch_id).join(Subject, Subject.id == ClassSchedule.subject_id)
                             .where(ClassSchedule.teacher_id == T, ClassSchedule.is_active.is_(True)).distinct()).all()
    pending_eval = db.execute(select(Assignment.id, Assignment.title, func.count(Submission.id)).join(Submission, Submission.assignment_id == Assignment.id)
                              .where(Assignment.teacher_id == T, Submission.status.in_(("submitted", "late", "under_review"))).group_by(Assignment.id)).all()
    deadlines = db.scalars(select(Assignment).where(Assignment.teacher_id == T, Assignment.status == "submission_open", Assignment.due_at >= datetime.now(timezone.utc))
                           .order_by(Assignment.due_at).limit(10)).all()
    m0 = month_start(today)
    hours = db.scalar(select(func.coalesce(func.sum(TeacherAttendance.teaching_minutes), 0)).join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
                      .where(TeacherAttendance.teacher_id == T, ClassSession.session_date.between(m0, today)))
    sessions_month = db.scalar(select(func.count()).where(ClassSession.institute_id == I, mine, ClassSession.session_date.between(m0, today),
                                                          ClassSession.status == "completed"))
    students = db.scalar(select(func.count(distinct(StudentEnrollment.student_id))).where(StudentEnrollment.batch_id.in_(p.batch_ids or [uuid.uuid4()]),
                                                                                         StudentEnrollment.status == "active"))
    return {
        "date": today,
        "todays_classes": [session_out(s, L) for s in upcoming if s.session_date == today],
        "upcoming_classes": [session_out(s, L) for s in upcoming if s.session_date > today][:15],
        "attendance_pending": [session_out(s, L) for s in pending_att],
        "batches_subjects": [{"batch": b, "subject": s, "batch_id": bid} for b, s, bid in assignments],
        "student_count": students,
        "evaluations_pending": [{"assignment_id": a, "title": t, "count": c} for a, t, c in pending_eval],
        "upcoming_deadlines": [{"id": a.id, "title": a.title, "due_at": a.due_at} for a in deadlines],
        "recent_materials": [{"id": m.id, "title": m.title, "created_at": m.created_at} for m in db.scalars(
            select(Material).where(Material.institute_id == I, Material.is_archived.is_(False),
                                   or_(Material.created_by_id == p.user_id, Material.batch_id.in_(p.batch_ids or [uuid.uuid4()])))
            .order_by(Material.created_at.desc()).limit(6))],
        "workload": {"sessions_this_month": sessions_month, "teaching_hours_this_month": round((hours or 0) / 60, 1)},
        "leaves": [{"id": l.id, "leave_type": l.leave_type, "start_date": l.start_date, "end_date": l.end_date, "status": l.status} for l in db.scalars(
            select(TeacherLeave).where(TeacherLeave.teacher_id == T).order_by(TeacherLeave.start_date.desc()).limit(5))],
    }


# ----------------------------------------------------------------------------- student & parent dashboards


def _student_dashboard(db: Session, p: Principal, student: Student) -> dict:
    from app.api.v1.classes import _labels, session_out
    from app.api.v1.people import attendance_summary

    I = p.institute_id
    today = today_local(db, I)
    batch_ids = list(db.scalars(select(StudentEnrollment.batch_id).where(StudentEnrollment.student_id == student.id, StudentEnrollment.status == "active")))
    week = db.scalars(select(ClassSession).where(ClassSession.batch_id.in_(batch_ids or [uuid.uuid4()]),
                                                 ClassSession.session_date.between(today, today + timedelta(days=6))).order_by(ClassSession.scheduled_start)).all()
    L = _labels(db, list(week))
    now = datetime.now(timezone.utc)
    pending = db.execute(
        select(Assignment.id, Assignment.title, Assignment.due_at, Submission.status)
        .outerjoin(Submission, and_(Submission.assignment_id == Assignment.id, Submission.student_id == student.id))
        .where(Assignment.batch_id.in_(batch_ids or [uuid.uuid4()]), Assignment.status == "submission_open",
               or_(Submission.id.is_(None), Submission.status.in_(("draft", "resubmission_requested"))))
        .order_by(Assignment.due_at).limit(15)).all()
    graded = db.execute(
        select(Assignment.title, AssignmentGrade.marks, Assignment.max_marks, AssignmentGrade.feedback, AssignmentGrade.created_at)
        .join(Submission, Submission.assignment_id == Assignment.id).join(AssignmentGrade, AssignmentGrade.submission_id == Submission.id)
        .where(Submission.student_id == student.id, AssignmentGrade.is_current.is_(True)).order_by(AssignmentGrade.created_at.desc()).limit(10)).all()
    absences = db.execute(select(ClassSession.session_date, Subject.name, StudentAttendance.status).join(ClassSession, ClassSession.id == StudentAttendance.session_id)
                          .join(Subject, Subject.id == ClassSession.subject_id).where(StudentAttendance.student_id == student.id,
                                                                                    StudentAttendance.status == "absent")
                          .order_by(ClassSession.session_date.desc()).limit(10)).all()
    results = db.execute(select(Examination.name, Subject.name, ExamResult.marks_obtained, ExamResult.max_marks, ExamResult.percentage, ExamResult.grade)
                         .join(Examination, Examination.id == ExamResult.examination_id).join(Subject, Subject.id == Examination.subject_id)
                         .where(ExamResult.student_id == student.id, ExamResult.status == "published").order_by(Examination.scheduled_start.desc().nullslast()).limit(10)).all()
    out = {
        "student": {"id": student.id, "full_name": student.full_name, "student_code": student.student_code},
        "todays_classes": [session_out(s, L) for s in week if s.session_date == today],
        "week_timetable": [session_out(s, L) for s in week],
        "attendance": attendance_summary(db, student.id),
        "recent_absences": [{"date": d, "subject": s, "status": st} for d, s, st in absences],
        "pending_homework": [{"id": a, "title": t, "due_at": d, "status": s or "not_submitted", "overdue": d < now} for a, t, d, s in pending],
        "grades_feedback": [{"title": t, "marks": m, "max_marks": mx, "feedback": fb, "at": at} for t, m, mx, fb, at in graded],
        "results": [{"exam": e, "subject": s, "marks": m, "max_marks": mx, "percentage": pc, "grade": g} for e, s, m, mx, pc, g in results],
        "recent_materials": [{"id": m.id, "title": m.title, "category": m.category, "created_at": m.created_at} for m in db.scalars(
            select(Material).where(Material.batch_id.in_(batch_ids or [uuid.uuid4()]), Material.visibility.in_(("batch", "institute")),
                                   Material.is_archived.is_(False)).order_by(Material.created_at.desc()).limit(6))],
    }
    if feature_flags.is_enabled(db, I, "billing"):
        invs = db.scalars(select(Invoice).where(Invoice.student_id == student.id, Invoice.status.in_(("issued", "partially_paid", "overdue")))
                          .order_by(Invoice.due_date)).all()
        out["fees"] = {"balance": finance.student_balance(db, student.id),
                       "open_invoices": [{"id": i.id, "invoice_number": i.invoice_number, "due_date": i.due_date, "balance_due": i.balance_due, "status": i.status} for i in invs],
                       "recent_payments": [{"id": x.id, "receipt_number": x.receipt_number, "paid_at": x.paid_at, "amount": x.amount, "method": x.method}
                                           for x in db.scalars(select(Payment).where(Payment.student_id == student.id, Payment.status == "completed")
                                                               .order_by(Payment.paid_at.desc()).limit(5))]}
    return out


@router.get("/dashboard/student")
def student_dashboard(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if not p.student_id:
        raise Forbidden("Student dashboard requires a student profile")
    return _student_dashboard(db, p, db.get(Student, p.student_id))


@router.get("/dashboard/parent")
def parent_dashboard(student_id: uuid.UUID | None = None, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if not p.parent_id:
        raise Forbidden("Parent dashboard requires a parent profile")
    if not feature_flags.is_enabled(db, p.institute_id, "parent_portal"):
        raise Forbidden("The parent portal is disabled")
    children = db.scalars(select(Student).where(Student.id.in_(p.linked_student_ids or [uuid.uuid4()])).order_by(Student.full_name)).all()
    if not children:
        return {"children": [], "selected": None}
    sel = next((c for c in children if c.id == student_id), children[0]) if student_id is None or student_id in p.linked_student_ids else None
    if sel is None:
        raise Forbidden("This student is not linked to your account")
    from app.models import StudentParent

    link = db.scalar(select(StudentParent).where(StudentParent.parent_id == p.parent_id, StudentParent.student_id == sel.id))
    data = _student_dashboard(db, p, sel)
    if link and not link.can_view_fees:
        data.pop("fees", None)
    if link and not link.can_view_academics:
        for k in ("grades_feedback", "results", "pending_homework"):
            data.pop(k, None)
    return {"children": [{"id": c.id, "full_name": c.full_name, "student_code": c.student_code} for c in children], "selected": data}


# ----------------------------------------------------------------------------- reports registry

ReportFn = Callable[[Session, Principal, dict], tuple[str, list[str], list[list[Any]]]]
REPORTS: dict[str, tuple[str, str, str, ReportFn]] = {}  # key -> (category, title, required perm, fn)


def report(key: str, category: str, title: str, perm: str):
    def deco(fn: ReportFn):
        REPORTS[key] = (category, title, perm, fn)
        return fn

    return deco


def _range(params: dict, default_days: int = 30) -> tuple[date, date]:
    end = date.fromisoformat(params["end"]) if params.get("end") else date.today()
    start = date.fromisoformat(params["start"]) if params.get("start") else end - timedelta(days=default_days)
    if end < start:
        raise ValidationFailed("End date must be after start date")
    return start, end


def _uuid(params: dict, key: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(params[key]) if params.get(key) else None
    except ValueError:
        raise ValidationFailed(f"Invalid {key}")


def _teacher_scope(p: Principal, batch_col):
    if p.is_staff:
        return true()
    return batch_col.in_(p.batch_ids or [uuid.uuid4()])


def _att_base(db, p, params):
    start, end = _range(params)
    q = (select(func.count().label("total"), func.sum(case((StudentAttendance.status == "present", 1), else_=0)).label("present"),
                func.sum(case((StudentAttendance.status == "late", 1), else_=0)).label("late"),
                func.sum(case((StudentAttendance.status == "absent", 1), else_=0)).label("absent"),
                func.sum(case((StudentAttendance.status == "excused", 1), else_=0)).label("excused"),
                func.sum(case((StudentAttendance.status == "approved_leave", 1), else_=0)).label("leave"))
         .select_from(StudentAttendance).join(ClassSession, ClassSession.id == StudentAttendance.session_id)
         .where(ClassSession.institute_id == p.institute_id, ClassSession.session_date.between(start, end), ClassSession.status != "cancelled",
                bscope(p, ClassSession.branch_id), _teacher_scope(p, ClassSession.batch_id)))
    for key, col in (("batch_id", ClassSession.batch_id), ("subject_id", ClassSession.subject_id), ("teacher_id", ClassSession.scheduled_teacher_id)):
        if _uuid(params, key):
            q = q.where(col == _uuid(params, key))
    return q, start, end


def _att_rows(rows, label_cols: int):
    out = []
    for r in rows:
        labels, (t, pr, lt, ab, ex, lv) = list(r[:label_cols]), r[label_cols:]
        out.append(labels + [t, pr or 0, lt or 0, ab or 0, ex or 0, lv or 0, pct((pr or 0) + (lt or 0), t)])
    return out


ATT_HEAD = ["Sessions", "Present", "Late", "Absent", "Excused", "Approved leave", "Attendance %"]


@report("student-attendance", "Academic", "Student attendance", "attendance.read_own")
def r_student_att(db, p, params):
    q, s, e = _att_base(db, p, params)
    q = q.add_columns(Student.full_name, Student.student_code).join(Student, Student.id == StudentAttendance.student_id).group_by(Student.full_name, Student.student_code)
    rows = db.execute(q).all()
    return f"Student attendance {s:%d-%m-%Y} – {e:%d-%m-%Y}", ["Student", "Code"] + ATT_HEAD, _att_rows([r[-2:] + r[:-2] for r in rows], 2)


@report("subject-attendance", "Academic", "Subject-wise attendance", "attendance.read_own")
def r_subject_att(db, p, params):
    q, s, e = _att_base(db, p, params)
    q = q.add_columns(Subject.name).join(Subject, Subject.id == ClassSession.subject_id).group_by(Subject.name)
    return f"Subject attendance {s:%d-%m-%Y} – {e:%d-%m-%Y}", ["Subject"] + ATT_HEAD, _att_rows([r[-1:] + r[:-1] for r in db.execute(q).all()], 1)


@report("batch-attendance", "Academic", "Batch-wise attendance", "attendance.read_own")
def r_batch_att(db, p, params):
    q, s, e = _att_base(db, p, params)
    q = q.add_columns(Batch.name).join(Batch, Batch.id == ClassSession.batch_id).group_by(Batch.name)
    return f"Batch attendance {s:%d-%m-%Y} – {e:%d-%m-%Y}", ["Batch"] + ATT_HEAD, _att_rows([r[-1:] + r[:-1] for r in db.execute(q).all()], 1)


@report("monthly-attendance", "Academic", "Monthly attendance", "attendance.read_own")
def r_month_att(db, p, params):
    params = {**params, "start": params.get("start") or (date.today() - timedelta(days=365)).isoformat()}
    q, s, e = _att_base(db, p, params)
    m = func.to_char(ClassSession.session_date, "YYYY-MM")
    q = q.add_columns(m).group_by(m).order_by(m)
    return "Monthly attendance", ["Month"] + ATT_HEAD, _att_rows([r[-1:] + r[:-1] for r in db.execute(q).all()], 1)


@report("teacher-attendance", "Academic", "Teacher attendance & teaching hours", "teacher_attendance.read")
def r_teacher_att(db, p, params):
    start, end = _range(params)
    rows = []
    for t in db.scalars(select(Teacher).where(Teacher.institute_id == p.institute_id, bscope(p, Teacher.branch_id)).order_by(Teacher.full_name)):
        scheduled = db.scalar(select(func.count()).where(ClassSession.scheduled_teacher_id == t.id, ClassSession.session_date.between(start, end)))
        cancelled = db.scalar(select(func.count()).where(ClassSession.scheduled_teacher_id == t.id, ClassSession.session_date.between(start, end),
                                                         ClassSession.status == "cancelled"))
        att = dict(db.execute(select(TeacherAttendance.status, func.count()).join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
                              .where(TeacherAttendance.teacher_id == t.id, ClassSession.session_date.between(start, end)).group_by(TeacherAttendance.status)).all())
        subs = db.scalar(select(func.count()).select_from(ClassSessionTeacher).join(ClassSession, ClassSession.id == ClassSessionTeacher.session_id)
                         .where(ClassSessionTeacher.teacher_id == t.id, ClassSessionTeacher.role == "substitute", ClassSession.session_date.between(start, end)))
        minutes = db.scalar(select(func.coalesce(func.sum(TeacherAttendance.teaching_minutes), 0)).join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
                            .where(TeacherAttendance.teacher_id == t.id, TeacherAttendance.status.in_(PRESENT), ClassSession.session_date.between(start, end)))
        conducted = att.get("present", 0) + att.get("late", 0)
        missed = att.get("absent", 0) + att.get("on_leave", 0)
        rows.append([t.full_name, scheduled, cancelled, conducted, missed, subs, round((minutes or 0) / 60, 1)])
    return f"Teacher attendance {start:%d-%m-%Y} – {end:%d-%m-%Y}", ["Teacher", "Scheduled", "Cancelled", "Conducted", "Missed", "Substitute sessions", "Teaching hours"], rows


@report("class-completion", "Academic", "Class completion & cancellation", "sessions.read_own")
def r_completion(db, p, params):
    start, end = _range(params)
    rows = db.execute(select(Batch.name, Subject.name, func.count(),
                             *[func.sum(case((ClassSession.status == s, 1), else_=0)) for s in ("completed", "cancelled", "postponed", "teacher_absent", "scheduled")],
                             func.sum(case((ClassSession.session_type == "makeup", 1), else_=0)))
                      .join(Batch, Batch.id == ClassSession.batch_id).join(Subject, Subject.id == ClassSession.subject_id)
                      .where(ClassSession.institute_id == p.institute_id, ClassSession.session_date.between(start, end), bscope(p, ClassSession.branch_id),
                             _teacher_scope(p, ClassSession.batch_id)).group_by(Batch.name, Subject.name).order_by(Batch.name)).all()
    return "Class completion", ["Batch", "Subject", "Total", "Completed", "Cancelled", "Postponed", "Teacher absent", "Still scheduled", "Makeup"], [
        [b, s, t] + [int(x or 0) for x in rest] for b, s, t, *rest in rows]


@report("makeup-sessions", "Academic", "Makeup sessions", "sessions.read_own")
def r_makeup(db, p, params):
    start, end = _range(params)
    rows = db.execute(select(ClassSession.session_date, Batch.name, Subject.name, Teacher.full_name, ClassSession.status, ClassSession.remarks)
                      .join(Batch, Batch.id == ClassSession.batch_id).join(Subject, Subject.id == ClassSession.subject_id)
                      .join(Teacher, Teacher.id == ClassSession.scheduled_teacher_id)
                      .where(ClassSession.institute_id == p.institute_id, ClassSession.session_type == "makeup",
                             ClassSession.session_date.between(start, end), bscope(p, ClassSession.branch_id), _teacher_scope(p, ClassSession.batch_id))
                      .order_by(ClassSession.session_date)).all()
    return "Makeup sessions", ["Date", "Batch", "Subject", "Teacher", "Status", "Remarks"], [list(r) for r in rows]


@report("teacher-workload", "Academic", "Teacher workload", "sessions.read_own")
def r_workload(db, p, params):
    start, end = _range(params)
    q = (select(Teacher.full_name, func.count(ClassSession.id), func.sum(case((ClassSession.status == "completed", 1), else_=0)),
                func.sum(extract("epoch", ClassSession.scheduled_end - ClassSession.scheduled_start) / 3600))
         .join(ClassSession, ClassSession.scheduled_teacher_id == Teacher.id)
         .where(Teacher.institute_id == p.institute_id, ClassSession.session_date.between(start, end), ClassSession.status != "cancelled",
                bscope(p, ClassSession.branch_id)).group_by(Teacher.full_name).order_by(Teacher.full_name))
    if not p.is_staff:
        q = q.where(Teacher.id == p.teacher_id)
    return "Teacher workload", ["Teacher", "Scheduled sessions", "Completed", "Scheduled hours"], [[n, c, int(d or 0), round(float(h or 0), 1)] for n, c, d, h in db.execute(q).all()]


@report("syllabus-completion", "Academic", "Syllabus completion", "syllabus.read")
def r_syllabus(db, p, params):
    from app.api.v1.learning import syllabus_progress

    rows = syllabus_progress(_uuid(params, "batch_id"), _uuid(params, "subject_id"), _uuid(params, "teacher_id"), _uuid(params, "course_id"), db, p)
    return "Syllabus completion", ["Batch", "Subject", "Chapters", "Completed", "In progress", "Delayed", "Coverage %"], [
        [r["batch"], r["subject"], r["total_chapters"], r["completed"], r["in_progress"], r["delayed"], r["coverage_percent"]] for r in rows]


@report("homework-submission", "Academic", "Homework submission & evaluation", "assignments.read_own")
def r_homework(db, p, params):
    start, end = _range(params, 60)
    rows = []
    for a, bn, sn, tn in db.execute(select(Assignment, Batch.name, Subject.name, Teacher.full_name).join(Batch, Batch.id == Assignment.batch_id)
                                    .join(Subject, Subject.id == Assignment.subject_id).join(Teacher, Teacher.id == Assignment.teacher_id)
                                    .where(Assignment.institute_id == p.institute_id, Assignment.status != "draft",
                                           func.date(Assignment.due_at).between(start, end), bscope(p, Assignment.branch_id),
                                           _teacher_scope(p, Assignment.batch_id)).order_by(Assignment.due_at)).all():
        c = dict(db.execute(select(Submission.status, func.count()).where(Submission.assignment_id == a.id).group_by(Submission.status)).all())
        assigned = db.scalar(select(func.count(distinct(StudentEnrollment.student_id))).where(StudentEnrollment.batch_id == a.batch_id,
                                                                                             StudentEnrollment.start_date <= func.date(a.due_at)))
        submitted = sum(v for k, v in c.items() if k != "draft")
        late = db.scalar(select(func.count()).where(Submission.assignment_id == a.id, Submission.is_late.is_(True)))
        rows.append([a.title, bn, sn, tn, a.due_at.strftime("%d-%m-%Y"), assigned, submitted, max(assigned - submitted, 0), late,
                     c.get("submitted", 0) + c.get("late", 0) + c.get("under_review", 0), c.get("evaluated", 0)])
    return "Homework submission", ["Assignment", "Batch", "Subject", "Teacher", "Due", "Assigned", "Submitted", "Not submitted", "Late",
                                   "Pending evaluation", "Evaluated"], rows


@report("exam-performance", "Academic", "Examination performance", "results.read_own")
def r_exams(db, p, params):
    start, end = _range(params, 180)
    rows = db.execute(select(Examination.name, Batch.name, Subject.name, func.count(ExamResult.id), func.avg(ExamResult.percentage),
                             func.max(ExamResult.percentage), func.min(ExamResult.percentage),
                             func.sum(case((ExamResult.marks_obtained >= Examination.pass_marks, 1), else_=0)),
                             func.sum(case((ExamResult.is_absent.is_(True), 1), else_=0)))
                      .join(ExamResult, ExamResult.examination_id == Examination.id).join(Batch, Batch.id == Examination.batch_id)
                      .join(Subject, Subject.id == Examination.subject_id)
                      .where(Examination.institute_id == p.institute_id, func.coalesce(func.date(Examination.scheduled_start), func.date(Examination.created_at)).between(start, end),
                             bscope(p, Examination.branch_id), _teacher_scope(p, Examination.batch_id))
                      .group_by(Examination.id, Examination.name, Batch.name, Subject.name)).all()
    return "Examination performance", ["Exam", "Batch", "Subject", "Results", "Average %", "Highest %", "Lowest %", "Passed", "Absent"], [
        [e, b, s, n, round(float(a or 0), 1), mx, mn, int(ps or 0), int(ab or 0)] for e, b, s, n, a, mx, mn, ps, ab in rows]


@report("student-progress", "Academic", "Student progress", "results.read_own")
def r_progress(db, p, params):
    sid = _uuid(params, "student_id")
    q = (select(Student.full_name, Examination.name, Subject.name, func.date(Examination.scheduled_start), ExamResult.percentage, ExamResult.grade, ExamResult.rank)
         .join(ExamResult, ExamResult.student_id == Student.id).join(Examination, Examination.id == ExamResult.examination_id)
         .join(Subject, Subject.id == Examination.subject_id).where(Student.institute_id == p.institute_id, bscope(p, Student.branch_id)))
    if sid:
        q = q.where(Student.id == sid)
    if not p.is_staff:
        q = q.where(or_(Student.id.in_(p.linked_student_ids or [uuid.uuid4()]), Examination.batch_id.in_(p.batch_ids or [uuid.uuid4()])))
        if not p.teacher_id:
            q = q.where(ExamResult.status == "published")
    return "Student progress", ["Student", "Exam", "Subject", "Date", "%", "Grade", "Rank"], [list(r) for r in db.execute(q.order_by(Student.full_name, Examination.scheduled_start)).all()]


# ----------------------------------------------------------------------------- financial reports


def _pay_range(db, p, params):
    start, end = _range(params)
    return start, end, day_bounds(db, p, start)[0], day_bounds(db, p, end)[1]


@report("daily-collection", "Financial", "Daily collection", "payments.read")
def r_daily(db, p, params):
    start, end, a, b = _pay_range(db, p, params)
    tz = institute_tz(db, p.institute_id).key
    d = func.date(func.timezone(tz, Payment.paid_at))
    rows = db.execute(select(d, Payment.method, func.count(), func.sum(Payment.amount)).where(
        Payment.institute_id == p.institute_id, Payment.status == "completed", Payment.paid_at.between(a, b), bscope(p, Payment.branch_id))
        .group_by(d, Payment.method).order_by(d)).all()
    return "Daily collection", ["Date", "Method", "Payments", "Amount"], [list(r) for r in rows]


@report("monthly-collection", "Financial", "Monthly collection", "payments.read")
def r_monthly(db, p, params):
    params = {**params, "start": params.get("start") or (date.today() - timedelta(days=365)).isoformat()}
    start, end, a, b = _pay_range(db, p, params)
    m = func.to_char(Payment.paid_at, "YYYY-MM")
    rows = db.execute(select(m, func.count(), func.sum(Payment.amount)).where(
        Payment.institute_id == p.institute_id, Payment.status == "completed", Payment.paid_at.between(a, b), bscope(p, Payment.branch_id))
        .group_by(m).order_by(m)).all()
    return "Monthly collection", ["Month", "Payments", "Amount"], [list(r) for r in rows]


@report("revenue-by", "Financial", "Revenue by course / subject / batch / branch", "invoices.read")
def r_revenue_by(db, p, params):
    start, end = _range(params, 90)
    dim = params.get("dimension", "course")
    base = (select(func.sum(InvoiceItem.amount)).join(Invoice, Invoice.id == InvoiceItem.invoice_id)
            .where(Invoice.institute_id == p.institute_id, Invoice.status.notin_(("draft", "cancelled")), Invoice.issue_date.between(start, end),
                   bscope(p, Invoice.branch_id)))
    if dim == "subject":
        q = base.add_columns(func.coalesce(Subject.name, "Unassigned")).outerjoin(Subject, Subject.id == InvoiceItem.subject_id).group_by(Subject.name)
    elif dim == "branch":
        q = base.add_columns(Branch.name).join(Branch, Branch.id == Invoice.branch_id).group_by(Branch.name)
    elif dim == "batch":
        q = base.add_columns(func.coalesce(Batch.name, "Unassigned")).outerjoin(StudentFeeAgreement, StudentFeeAgreement.id == Invoice.agreement_id).outerjoin(
            Batch, Batch.id == StudentFeeAgreement.batch_id).group_by(Batch.name)
    else:
        dim = "course"
        q = base.add_columns(func.coalesce(Course.name, "Unassigned")).outerjoin(StudentFeeAgreement, StudentFeeAgreement.id == Invoice.agreement_id).outerjoin(
            FeePlan, FeePlan.id == StudentFeeAgreement.fee_plan_id).outerjoin(Course, Course.id == FeePlan.course_id).group_by(Course.name)
    return f"Invoiced revenue by {dim}", [dim.title(), "Invoiced amount"], [[r[1], r[0]] for r in db.execute(q).all()]


@report("outstanding-fees", "Financial", "Outstanding fees", "invoices.read")
def r_outstanding(db, p, params):
    today = date.today()
    rows = db.execute(select(Student.student_code, Student.full_name, func.count(Invoice.id), func.sum(Invoice.balance_due),
                             func.sum(case((Invoice.due_date < today, Invoice.balance_due), else_=0)), func.min(Invoice.due_date))
                      .join(Invoice, Invoice.student_id == Student.id)
                      .where(Invoice.institute_id == p.institute_id, Invoice.status.in_(("issued", "partially_paid", "overdue")), Invoice.balance_due > 0,
                             bscope(p, Invoice.branch_id)).group_by(Student.student_code, Student.full_name).order_by(func.sum(Invoice.balance_due).desc())).all()
    return "Outstanding fees", ["Code", "Student", "Open invoices", "Outstanding", "Overdue", "Oldest due"], [list(r) for r in rows]


@report("overdue-invoices", "Financial", "Overdue invoices", "invoices.read")
def r_overdue(db, p, params):
    today = date.today()
    rows = db.execute(select(Invoice.invoice_number, Student.full_name, Invoice.issue_date, Invoice.due_date, Invoice.total, Invoice.balance_due)
                      .join(Student, Student.id == Invoice.student_id).where(Invoice.institute_id == p.institute_id, Invoice.balance_due > 0,
                                                                            Invoice.status.in_(("issued", "partially_paid", "overdue")), Invoice.due_date < today,
                                                                            bscope(p, Invoice.branch_id)).order_by(Invoice.due_date)).all()
    return "Overdue invoices", ["Invoice", "Student", "Issued", "Due", "Total", "Balance", "Days overdue"], [list(r) + [(today - r[3]).days] for r in rows]


@report("discounts-scholarships", "Financial", "Discounts & scholarships", "invoices.read")
def r_discounts(db, p, params):
    start, end = _range(params, 365)
    rows = db.execute(select(Student.full_name, func.sum(Invoice.discount_total), func.count(Invoice.id)).join(Student, Student.id == Invoice.student_id)
                      .where(Invoice.institute_id == p.institute_id, Invoice.discount_total > 0, Invoice.status.notin_(("draft", "cancelled")),
                             Invoice.issue_date.between(start, end), bscope(p, Invoice.branch_id)).group_by(Student.full_name)).all()
    sch = dict(db.execute(select(Student.full_name, func.string_agg(StudentFeeAgreement.scholarship_name, ", ")).join(Student, Student.id == StudentFeeAgreement.student_id)
                          .where(StudentFeeAgreement.institute_id == p.institute_id, StudentFeeAgreement.scholarship_amount > 0).group_by(Student.full_name)).all())
    return "Discounts & scholarships", ["Student", "Total discount", "Invoices", "Scholarships"], [[n, d, c, sch.get(n)] for n, d, c in rows]


@report("refunds", "Financial", "Refunds", "refunds.read")
def r_refunds(db, p, params):
    rows = db.execute(select(Refund.refund_number, Student.full_name, Refund.amount, Refund.method, Refund.status, Refund.reason, Refund.processed_at)
                      .join(Student, Student.id == Refund.student_id).where(Refund.institute_id == p.institute_id, bscope(p, Refund.branch_id))
                      .order_by(Refund.created_at.desc())).all()
    return "Refunds", ["Refund no.", "Student", "Amount", "Method", "Status", "Reason", "Processed"], [list(r) for r in rows]


@report("expenses", "Financial", "Expenses by category", "expenses.read")
def r_expenses(db, p, params):
    start, end = _range(params, 90)
    rows = db.execute(select(ExpenseCategory.name, func.count(Expense.id), func.sum(Expense.amount), func.sum(Expense.tax_amount))
                      .join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
                      .where(Expense.institute_id == p.institute_id, Expense.status.in_(("approved", "paid")), Expense.expense_date.between(start, end),
                             bscope(p, Expense.branch_id)).group_by(ExpenseCategory.name)).all()
    return "Expenses by category", ["Category", "Entries", "Amount", "Tax"], [list(r) for r in rows]


def _income_expense(db, p, start: date, end: date) -> list[list[Any]]:
    a, b = day_bounds(db, p, start)[0], day_bounds(db, p, end)[1]
    m_pay = func.to_char(Payment.paid_at, "YYYY-MM")
    income = dict(db.execute(select(m_pay, func.sum(Payment.amount)).where(Payment.institute_id == p.institute_id, Payment.status == "completed",
                                                                         Payment.paid_at.between(a, b), bscope(p, Payment.branch_id)).group_by(m_pay)).all())
    m_ref = func.to_char(Refund.processed_at, "YYYY-MM")
    refunds = dict(db.execute(select(m_ref, func.sum(Refund.amount)).where(Refund.institute_id == p.institute_id, Refund.status == "processed",
                                                                          Refund.processed_at.between(a, b), bscope(p, Refund.branch_id)).group_by(m_ref)).all())
    m_exp = func.to_char(Expense.expense_date, "YYYY-MM")
    expenses = dict(db.execute(select(m_exp, func.sum(Expense.amount + Expense.tax_amount)).where(
        Expense.institute_id == p.institute_id, Expense.status.in_(("approved", "paid")), Expense.expense_date.between(start, end),
        bscope(p, Expense.branch_id)).group_by(m_exp)).all())
    m_pr = func.to_char(TeacherPayout.paid_at, "YYYY-MM")
    payroll = dict(db.execute(select(m_pr, func.sum(TeacherPayout.amount)).where(TeacherPayout.institute_id == p.institute_id, TeacherPayout.status == "paid",
                                                                                TeacherPayout.paid_at.between(a, b)).group_by(m_pr)).all())
    months = sorted(set(income) | set(expenses) | set(payroll) | set(refunds))
    rows = []
    for m in months:
        i, r, e, pr = (Decimal(x.get(m) or 0) for x in (income, refunds, expenses, payroll))
        rows.append([m, i, r, e, pr, i - r - e - pr])
    return rows


@report("income-expenditure", "Financial", "Income & expenditure", "accounting.read")
def r_ie(db, p, params):
    start, end = _range(params, 365)
    return "Income & expenditure (cash basis)", ["Month", "Collections", "Refunds", "Expenses", "Payroll", "Net"], _income_expense(db, p, start, end)


@report("profit-loss", "Financial", "Profit & loss", "accounting.read")
def r_pl(db, p, params):
    start, end = _range(params, 365)
    rows = _income_expense(db, p, start, end)
    tot = [sum((r[i] for r in rows), Decimal("0")) for i in range(1, 6)]
    invoiced = db.scalar(select(func.coalesce(func.sum(Invoice.total), 0)).where(Invoice.institute_id == p.institute_id,
                                                                                Invoice.status.notin_(("draft", "cancelled")),
                                                                                Invoice.issue_date.between(start, end), bscope(p, Invoice.branch_id)))
    return f"Profit & loss {start:%d-%m-%Y} – {end:%d-%m-%Y}", ["Line", "Amount"], [
        ["Fees invoiced (accrual)", invoiced], ["Fees collected", tot[0]], ["Refunds", tot[1]], ["Operating expenses", tot[2]],
        ["Teacher payroll", tot[3]], ["Net (cash basis)", tot[4]]]


@report("teacher-payroll", "Financial", "Teacher payroll", "payroll.read")
def r_payroll(db, p, params):
    q = (select(PayrollPeriod.name, Teacher.full_name, Payslip.payslip_number, Payslip.gross_amount, Payslip.deductions, Payslip.net_amount, Payslip.status)
         .join(PayrollPeriod, PayrollPeriod.id == Payslip.payroll_period_id).join(Teacher, Teacher.id == Payslip.teacher_id)
         .where(Payslip.institute_id == p.institute_id).order_by(PayrollPeriod.start_date.desc(), Teacher.full_name))
    if _uuid(params, "payroll_period_id"):
        q = q.where(PayrollPeriod.id == _uuid(params, "payroll_period_id"))
    return "Teacher payroll", ["Period", "Teacher", "Payslip", "Gross", "Deductions", "Net", "Status"], [list(r) for r in db.execute(q).all()]


# ----------------------------------------------------------------------------- business reports


@report("admission-conversion", "Business", "Admission conversion", "admissions.read")
def r_conversion(db, p, params):
    from app.api.v1.admissions import conversion

    start, end = _range(params, 365)
    data = conversion(start, end, db, p)
    return "Admission conversion by source", ["Source", "Enquiries", "Enrolled", "Lost", "Conversion %"], [
        [r["source"], r["enquiries"], r["enrolled"], r["lost"], r["conversion_percent"]] for r in data["by_source"]]


@report("student-acquisition", "Business", "Student acquisition", "students.read")
def r_acquisition(db, p, params):
    params = {**params, "start": params.get("start") or (date.today() - timedelta(days=365)).isoformat()}
    start, end = _range(params)
    m = func.to_char(Student.admission_date, "YYYY-MM")
    rows = db.execute(select(m, func.count()).where(Student.institute_id == p.institute_id, Student.admission_date.between(start, end),
                                                    bscope(p, Student.branch_id)).group_by(m).order_by(m)).all()
    return "New admissions per month", ["Month", "New students"], [list(r) for r in rows]


@report("student-retention", "Business", "Student retention", "students.read")
def r_retention(db, p, params):
    start, end = _range(params, 180)
    rows = []
    for c in db.scalars(select(Course).where(Course.institute_id == p.institute_id).order_by(Course.name)):
        at_start = db.scalar(select(func.count(distinct(StudentEnrollment.student_id))).where(
            StudentEnrollment.course_id == c.id, StudentEnrollment.start_date <= start,
            or_(StudentEnrollment.end_date.is_(None), StudentEnrollment.end_date >= start), bscope(p, StudentEnrollment.branch_id)))
        retained = db.scalar(select(func.count(distinct(StudentEnrollment.student_id))).where(
            StudentEnrollment.course_id == c.id, StudentEnrollment.start_date <= start,
            or_(StudentEnrollment.end_date.is_(None), StudentEnrollment.end_date >= end), bscope(p, StudentEnrollment.branch_id)))
        withdrawn = db.scalar(select(func.count(distinct(StudentEnrollment.student_id))).where(
            StudentEnrollment.course_id == c.id, StudentEnrollment.status == "withdrawn", StudentEnrollment.end_date.between(start, end)))
        rows.append([c.name, at_start, retained, withdrawn, pct(retained, at_start)])
    return f"Retention {start:%d-%m-%Y} – {end:%d-%m-%Y}", ["Course", "Enrolled at start", "Still enrolled at end", "Withdrawn", "Retention %"], rows


@report("batch-utilization", "Business", "Batch utilisation", "batches.read")
def r_batch_util(db, p, params):
    rows = db.execute(select(Batch.name, Batch.capacity, func.count(StudentEnrollment.id)).outerjoin(
        StudentEnrollment, and_(StudentEnrollment.batch_id == Batch.id, StudentEnrollment.status == "active"))
        .where(Batch.institute_id == p.institute_id, Batch.status == "active", bscope(p, Batch.branch_id)).group_by(Batch.id).order_by(Batch.name)).all()
    return "Batch utilisation", ["Batch", "Capacity", "Active students", "Utilisation %"], [[n, c, s, pct(s, c)] for n, c, s in rows]


@report("classroom-utilization", "Business", "Classroom utilisation", "classrooms.read")
def r_room_util(db, p, params):
    start, end = _range(params)
    hours_per_day = Decimal(params.get("open_hours_per_day") or 10)
    days = (end - start).days + 1
    rows = db.execute(select(Classroom.name, Classroom.capacity, func.count(ClassSession.id),
                             func.coalesce(func.sum(extract("epoch", ClassSession.scheduled_end - ClassSession.scheduled_start) / 3600), 0))
                      .outerjoin(ClassSession, and_(ClassSession.classroom_id == Classroom.id, ClassSession.session_date.between(start, end),
                                                    ClassSession.status != "cancelled"))
                      .where(Classroom.institute_id == p.institute_id, bscope(p, Classroom.branch_id)).group_by(Classroom.id).order_by(Classroom.name)).all()
    return "Classroom utilisation", ["Classroom", "Capacity", "Sessions", "Booked hours", f"Utilisation % ({hours_per_day}h/day)"], [
        [n, c, s, round(float(h), 1), pct(float(h), float(hours_per_day) * days)] for n, c, s, h in rows]


@report("teacher-utilization", "Business", "Teacher utilisation", "teachers.read")
def r_teacher_util(db, p, params):
    start, end = _range(params)
    rows = []
    for t in db.scalars(select(Teacher).where(Teacher.institute_id == p.institute_id, Teacher.employment_status == "active", bscope(p, Teacher.branch_id))):
        avail = Decimal("0")
        for a in db.scalars(select(TeacherAvailability).where(TeacherAvailability.teacher_id == t.id)):
            h = (datetime.strptime(a.end_time, "%H:%M") - datetime.strptime(a.start_time, "%H:%M")).seconds / 3600
            occurrences = sum(1 for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() == a.day_of_week)
            avail += Decimal(str(h)) * occurrences
        taught = db.scalar(select(func.coalesce(func.sum(TeacherAttendance.teaching_minutes), 0)).join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
                           .where(TeacherAttendance.teacher_id == t.id, TeacherAttendance.status.in_(PRESENT), ClassSession.session_date.between(start, end)))
        rows.append([t.full_name, round(float(avail), 1), round((taught or 0) / 60, 1), pct((taught or 0) / 60, float(avail)) if avail else None])
    return "Teacher utilisation", ["Teacher", "Available hours", "Taught hours", "Utilisation %"], rows


@report("branch-comparison", "Business", "Branch comparison", "reports.read")
def r_branches(db, p, params):
    start, end = _range(params, 90)
    a, b = day_bounds(db, p, start)[0], day_bounds(db, p, end)[1]
    rows = []
    for br in db.scalars(select(Branch).where(Branch.institute_id == p.institute_id, bscope(p, Branch.id)).order_by(Branch.name)):
        rows.append([br.name,
                     db.scalar(select(func.count()).where(Student.branch_id == br.id, Student.status == "active")),
                     db.scalar(select(func.count()).where(Teacher.branch_id == br.id, Teacher.employment_status == "active")),
                     db.scalar(select(func.count()).where(Batch.branch_id == br.id, Batch.status == "active")),
                     db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.branch_id == br.id, Payment.status == "completed", Payment.paid_at.between(a, b))),
                     db.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.branch_id == br.id, Expense.status.in_(("approved", "paid")),
                                                                                      Expense.expense_date.between(start, end))),
                     db.scalar(select(func.coalesce(func.sum(Invoice.balance_due), 0)).where(Invoice.branch_id == br.id, Invoice.status.in_(("issued", "partially_paid", "overdue"))))])
    return "Branch comparison", ["Branch", "Students", "Teachers", "Batches", "Collections", "Expenses", "Outstanding"], rows


@report("operational-cost", "Business", "Operational cost", "accounting.read")
def r_opcost(db, p, params):
    start, end = _range(params, 365)
    return "Operational cost", ["Month", "Expenses", "Payroll", "Total"], [[r[0], r[3], r[4], r[3] + r[4]] for r in _income_expense(db, p, start, end)]


# ----------------------------------------------------------------------------- report endpoints


@router.get("/reports")
def list_reports(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    out = []
    for key, (cat, title, perm, _) in REPORTS.items():
        base = perm.rsplit(".", 1)[0]
        if p.can(perm) or p.can(f"{base}.read") or (p.is_staff and p.can("reports.read")):
            out.append({"key": key, "category": cat, "title": title})
    return out


@router.get("/reports/{key}")
def run_report(key: str, request: Request, format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
               db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    if key not in REPORTS:
        raise NotFound("Unknown report")
    cat, title, perm, fn = REPORTS[key]
    base = perm.rsplit(".", 1)[0]
    if not (p.can(perm) or p.can(f"{base}.read")):
        raise Forbidden("You do not have access to this report")
    if cat == "Financial" and not (p.can("invoices.read") or p.can("accounting.read") or p.can("payroll.read") or p.can("payments.read")):
        raise Forbidden("Financial reports require finance permissions")
    params = {k: v for k, v in request.query_params.items() if k != "format"}
    try:
        heading, headers, rows = fn(db, p, params)
    except ValueError as e:
        raise ValidationFailed(str(e))
    if format == "json":
        return {"key": key, "title": heading, "headers": headers, "rows": rows}
    from app.services import audit

    audit.record(db, p, "reports", None, "export", new={"report": key, "format": format, "rows": len(rows)})
    db.commit()
    data = exporter.render(format, headers, rows, heading)
    return file_response(data, f"{key}-{date.today().isoformat()}.{format}", exporter.MIME[format])
