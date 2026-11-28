import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.common import ensure_student_access, file_response, get_tenant_obj
from app.api.deps import Principal, get_principal, require_perm
from app.api.v1.admin import create_user_account
from app.api.v1.files import download_url
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.crud.engine import REGISTRY, mask_fields, serialize
from app.db.session import get_db
from app.models import (
    Assignment,
    AssignmentGrade,
    AuditLog,
    Batch,
    ClassSchedule,
    ClassSession,
    ClassSessionTeacher,
    Course,
    Document,
    EmploymentRecord,
    ExamResult,
    Examination,
    FileDownloadLog,
    Institute,
    Invoice,
    LeaveBalance,
    Material,
    Parent,
    Payment,
    Payslip,
    Student,
    StudentAttendance,
    StudentEnrollment,
    StudentFeeAgreement,
    StudentParent,
    Subject,
    Submission,
    Teacher,
    TeacherAssignment,
    TeacherAttendance,
    TeacherLeave,
    User,
)
from app.services import audit, finance, notifications, numbering, pdf, storage
from app.services.scheduling import today_local

router = APIRouter(tags=["People"])


# ----------------------------------------------------------------------------- helpers


def _student(db: Session, p: Principal, student_id: uuid.UUID) -> Student:
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    ensure_student_access(db, p, s)
    return s


def attendance_summary(db: Session, student_id: uuid.UUID, start: date | None = None, end: date | None = None) -> dict:
    q = (
        select(StudentAttendance.status, func.count())
        .join(ClassSession, ClassSession.id == StudentAttendance.session_id)
        .where(StudentAttendance.student_id == student_id, ClassSession.status != "cancelled")
        .group_by(StudentAttendance.status)
    )
    if start:
        q = q.where(ClassSession.session_date >= start)
    if end:
        q = q.where(ClassSession.session_date <= end)
    counts = {k: v for k, v in db.execute(q).all()}
    total = sum(counts.values())
    present = counts.get("present", 0) + counts.get("late", 0)
    return {
        "total_sessions": total,
        "present": counts.get("present", 0),
        "late": counts.get("late", 0),
        "absent": counts.get("absent", 0),
        "excused": counts.get("excused", 0),
        "approved_leave": counts.get("approved_leave", 0),
        "percentage": round(present * 100 / total, 1) if total else None,
    }


# ----------------------------------------------------------------------------- student profile


@router.get("/students/{student_id}/profile")
def student_profile(student_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _student(db, p, student_id)
    staff = p.can("students.read")
    res = REGISTRY["students"]
    data = serialize(s, mask_fields(p, res))
    enrollments = db.execute(
        select(StudentEnrollment, Batch.name, Course.name)
        .join(Batch, Batch.id == StudentEnrollment.batch_id)
        .join(Course, Course.id == StudentEnrollment.course_id)
        .where(StudentEnrollment.student_id == s.id)
        .order_by(StudentEnrollment.start_date.desc())
    ).all()
    parents = db.execute(
        select(Parent, StudentParent.relation, StudentParent.is_primary)
        .join(StudentParent, StudentParent.parent_id == Parent.id)
        .where(StudentParent.student_id == s.id)
    ).all()
    by_subject = db.execute(
        select(
            Subject.name,
            func.count(),
            func.sum(case((StudentAttendance.status.in_(("present", "late")), 1), else_=0)),
        )
        .join(ClassSession, ClassSession.id == StudentAttendance.session_id)
        .join(Subject, Subject.id == ClassSession.subject_id)
        .where(StudentAttendance.student_id == s.id, ClassSession.status != "cancelled")
        .group_by(Subject.name)
    ).all()
    recent_att = db.execute(
        select(ClassSession.session_date, Subject.name, StudentAttendance.status, StudentAttendance.remarks)
        .join(ClassSession, ClassSession.id == StudentAttendance.session_id)
        .join(Subject, Subject.id == ClassSession.subject_id)
        .where(StudentAttendance.student_id == s.id)
        .order_by(ClassSession.scheduled_start.desc())
        .limit(30)
    ).all()
    homework = db.execute(
        select(Assignment.id, Assignment.title, Assignment.due_at, Submission.status, Submission.submitted_at, Submission.is_late,
               AssignmentGrade.marks, Assignment.max_marks, AssignmentGrade.feedback)
        .join(Submission, and_(Submission.assignment_id == Assignment.id, Submission.student_id == s.id), isouter=True)
        .join(AssignmentGrade, and_(AssignmentGrade.submission_id == Submission.id, AssignmentGrade.is_current.is_(True)), isouter=True)
        .where(Assignment.batch_id.in_([e[0].batch_id for e in enrollments] or [uuid.uuid4()]), Assignment.status != "draft")
        .order_by(Assignment.due_at.desc())
        .limit(50)
    ).all()
    results_q = (
        select(ExamResult, Examination.name, Examination.scheduled_start, Subject.name)
        .join(Examination, Examination.id == ExamResult.examination_id)
        .join(Subject, Subject.id == Examination.subject_id)
        .where(ExamResult.student_id == s.id)
        .order_by(Examination.scheduled_start.desc().nullslast())
    )
    if not (staff or p.teacher_id):
        results_q = results_q.where(ExamResult.status == "published")
    results = db.execute(results_q.limit(50)).all()
    out = {
        "student": data,
        "enrollments": [
            {"id": e.id, "batch_id": e.batch_id, "batch": bn, "course": cn, "start_date": e.start_date, "end_date": e.end_date,
             "status": e.status, "academic_year_id": e.academic_year_id}
            for e, bn, cn in enrollments
        ],
        "parents": [
            {"id": pr.id, "full_name": pr.full_name, "phone": pr.phone, "email": pr.email, "relation": rel, "is_primary": prim}
            for pr, rel, prim in parents
        ],
        "attendance": {
            "summary": attendance_summary(db, s.id),
            "by_subject": [{"subject": n, "total": t, "present": int(pr or 0), "percentage": round((pr or 0) * 100 / t, 1) if t else None}
                           for n, t, pr in by_subject],
            "recent": [{"date": d, "subject": sn, "status": st, "remarks": rm} for d, sn, st, rm in recent_att],
        },
        "homework": [
            {"assignment_id": a, "title": t, "due_at": due, "status": st or "not_submitted", "submitted_at": sa, "is_late": late,
             "marks": mk, "max_marks": mx, "feedback": fb}
            for a, t, due, st, sa, late, mk, mx, fb in homework
        ],
        "results": [
            {"exam": en, "subject": sn, "date": sd, "marks": r.marks_obtained, "max_marks": r.max_marks, "percentage": r.percentage,
             "grade": r.grade, "rank": r.rank, "status": r.status, "is_absent": r.is_absent, "remarks": r.remarks,
             "remedial_recommendation": r.remedial_recommendation}
            for r, en, sd, sn in results
        ],
    }
    can_fees = staff or p.can("invoices.read") or p.owns_student(s.id)
    if p.parent_id and not p.can("invoices.read"):
        link = db.scalar(select(StudentParent).where(StudentParent.student_id == s.id, StudentParent.parent_id == p.parent_id))
        can_fees = bool(link and link.can_view_fees)
    if can_fees and (p.can("invoices.read") or p.can("invoices.read_own")):
        invoices = db.scalars(select(Invoice).where(Invoice.student_id == s.id).order_by(Invoice.issue_date.desc()).limit(50)).all()
        payments = db.scalars(select(Payment).where(Payment.student_id == s.id).order_by(Payment.paid_at.desc()).limit(50)).all()
        out["fees"] = {
            "balance": finance.student_balance(db, s.id),
            "invoices": [{"id": i.id, "invoice_number": i.invoice_number, "issue_date": i.issue_date, "due_date": i.due_date,
                          "total": i.total, "balance_due": i.balance_due, "status": i.status} for i in invoices],
            "payments": [{"id": x.id, "receipt_number": x.receipt_number, "paid_at": x.paid_at, "amount": x.amount,
                          "method": x.method, "status": x.status} for x in payments],
            "agreements": [audit.snapshot(a) for a in db.scalars(select(StudentFeeAgreement).where(StudentFeeAgreement.student_id == s.id))],
        }
    if staff:
        docs = db.scalars(select(Document).where(Document.owner_type == "student", Document.owner_id == s.id,
                                                 Document.is_archived.is_(False)).order_by(Document.created_at.desc())).all()
        out["documents"] = [{"id": d.id, "title": d.title, "category": d.category, "original_filename": d.original_filename,
                             "version_number": d.version_number, "size_bytes": d.size_bytes, "created_at": d.created_at} for d in docs]
        out["material_access"] = [
            {"material": t, "downloaded_at": c}
            for t, c in db.execute(
                select(Material.title, FileDownloadLog.created_at)
                .join(Material, Material.id == FileDownloadLog.object_id)
                .where(FileDownloadLog.user_id == s.user_id, FileDownloadLog.object_type == "material")
                .order_by(FileDownloadLog.created_at.desc()).limit(50)
            ).all()
        ] if s.user_id else []
        out["timeline"] = [
            {"at": l.created_at, "action": l.action, "entity": l.entity_type, "actor": l.actor_email, "changes": l.new_values, "reason": l.reason}
            for l in db.scalars(
                select(AuditLog).where(
                    AuditLog.institute_id == p.institute_id,
                    or_(AuditLog.entity_id == s.id, AuditLog.new_values["student_id"].astext == str(s.id)),
                ).order_by(AuditLog.created_at.desc()).limit(100)
            )
        ]
    return out


# ----------------------------------------------------------------------------- lifecycle


class WithdrawIn(BaseModel):
    withdrawal_date: date
    reason: str = Field(min_length=3, max_length=1000)


class ReadmitIn(BaseModel):
    batch_id: uuid.UUID | None = None
    start_date: date
    reason: str | None = Field(default=None, max_length=1000)


class TransferBatchIn(BaseModel):
    enrollment_id: uuid.UUID
    to_batch_id: uuid.UUID
    effective_date: date
    reason: str = Field(min_length=3, max_length=1000)


class TransferBranchIn(BaseModel):
    branch_id: uuid.UUID
    effective_date: date
    reason: str = Field(min_length=3, max_length=1000)


class PromoteIn(BaseModel):
    from_batch_id: uuid.UUID
    to_batch_id: uuid.UUID
    effective_date: date
    student_ids: list[uuid.UUID] | None = None


def _check_capacity(db: Session, batch: Batch, adding: int = 1) -> None:
    active = db.scalar(select(func.count()).where(StudentEnrollment.batch_id == batch.id, StudentEnrollment.status == "active"))
    if batch.capacity and active + adding > batch.capacity:
        raise Conflict(f"Batch {batch.name} has insufficient capacity ({active}/{batch.capacity})")


def _enroll(db: Session, p: Principal, student: Student, batch: Batch, start: date, transferred_from: uuid.UUID | None = None,
            remarks: str | None = None) -> StudentEnrollment:
    if db.scalar(select(StudentEnrollment.id).where(StudentEnrollment.student_id == student.id, StudentEnrollment.batch_id == batch.id,
                                                    StudentEnrollment.status == "active")):
        raise Conflict(f"{student.full_name} is already actively enrolled in {batch.name}")
    e = StudentEnrollment(institute_id=p.institute_id, branch_id=batch.branch_id, student_id=student.id, batch_id=batch.id,
                          course_id=batch.course_id, academic_year_id=batch.academic_year_id, start_date=start, status="active",
                          transferred_from_id=transferred_from, remarks=remarks, created_by_id=p.user_id, updated_by_id=p.user_id)
    db.add(e)
    db.flush()
    return e


@router.post("/students/{student_id}/withdraw")
def withdraw_student(student_id: uuid.UUID, body: WithdrawIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("students.archive"))):
    s = get_tenant_obj(db, p, Student, student_id, lock=True, label="Student")
    if s.status == "withdrawn":
        raise Conflict("Student is already withdrawn")
    before = audit.snapshot(s)
    s.status = "withdrawn"
    s.withdrawal_date = body.withdrawal_date
    s.withdrawal_reason = body.reason
    db.execute(update(StudentEnrollment).where(StudentEnrollment.student_id == s.id, StudentEnrollment.status == "active")
               .values(status="withdrawn", end_date=body.withdrawal_date))
    db.execute(update(StudentFeeAgreement).where(StudentFeeAgreement.student_id == s.id, StudentFeeAgreement.status == "active")
               .values(status="ended", effective_to=body.withdrawal_date))
    if s.user_id:
        db.execute(update(User).where(User.id == s.user_id).values(is_active=False))
    old, new = audit.diff(before, audit.snapshot(s))
    audit.record(db, p, "students", s.id, "withdraw", old, new, body.reason, branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


@router.post("/students/{student_id}/readmit")
def readmit_student(student_id: uuid.UUID, body: ReadmitIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("students.write"))):
    s = get_tenant_obj(db, p, Student, student_id, lock=True, label="Student")
    if s.status == "active" and not s.is_archived:
        raise Conflict("Student is already active")
    s.status = "active"
    s.is_archived = False
    s.archived_at = None
    if s.user_id:
        db.execute(update(User).where(User.id == s.user_id).values(is_active=True))
    if body.batch_id:
        batch = get_tenant_obj(db, p, Batch, body.batch_id, label="Batch")
        _check_capacity(db, batch)
        _enroll(db, p, s, batch, body.start_date, remarks="Re-admission")
    audit.record(db, p, "students", s.id, "readmit", reason=body.reason, new={"batch_id": body.batch_id}, branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


@router.post("/students/{student_id}/transfer-batch")
def transfer_batch(student_id: uuid.UUID, body: TransferBatchIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("enrollments.write"))):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    old = get_tenant_obj(db, p, StudentEnrollment, body.enrollment_id, lock=True, label="Enrollment")
    if old.student_id != s.id or old.status != "active":
        raise ValidationFailed("Enrollment is not an active enrollment of this student")
    if body.effective_date <= old.start_date:
        raise ValidationFailed("Transfer date must be after the current enrollment start date")
    batch = get_tenant_obj(db, p, Batch, body.to_batch_id, label="Batch")
    if batch.id == old.batch_id:
        raise ValidationFailed("Target batch is the same as current batch")
    _check_capacity(db, batch)
    old.status = "transferred"
    old.end_date = body.effective_date - timedelta(days=1)
    new = _enroll(db, p, s, batch, body.effective_date, transferred_from=old.id, remarks=body.reason)
    kind = "course_transfer" if batch.course_id != old.course_id else "batch_transfer"
    audit.record(db, p, "students", s.id, kind, {"batch_id": old.batch_id}, {"batch_id": batch.id, "enrollment_id": new.id}, body.reason,
                 branch_id=s.branch_id)
    db.commit()
    return {"enrollment_id": new.id}


@router.post("/students/{student_id}/transfer-branch")
def transfer_branch(student_id: uuid.UUID, body: TransferBranchIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("students.write"))):
    s = get_tenant_obj(db, p, Student, student_id, lock=True, label="Student")
    from app.models import Branch

    br = get_tenant_obj(db, p, Branch, body.branch_id, label="Branch")
    if br.id == s.branch_id:
        raise ValidationFailed("Student is already in this branch")
    old_branch = s.branch_id
    db.execute(update(StudentEnrollment).where(StudentEnrollment.student_id == s.id, StudentEnrollment.status == "active")
               .values(status="transferred", end_date=body.effective_date - timedelta(days=1)))
    s.branch_id = br.id
    audit.record(db, p, "students", s.id, "branch_transfer", {"branch_id": old_branch}, {"branch_id": br.id}, body.reason, branch_id=br.id)
    db.commit()
    return {"ok": True, "note": "Active enrollments were closed; enroll the student into batches of the new branch."}


@router.post("/students/promote")
def promote_students(body: PromoteIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("enrollments.write"))):
    src = get_tenant_obj(db, p, Batch, body.from_batch_id, label="Batch")
    dst = get_tenant_obj(db, p, Batch, body.to_batch_id, label="Batch")
    q = select(StudentEnrollment).where(StudentEnrollment.batch_id == src.id, StudentEnrollment.status == "active").with_for_update()
    if body.student_ids:
        q = q.where(StudentEnrollment.student_id.in_(body.student_ids))
    rows = db.scalars(q).all()
    _check_capacity(db, dst, len(rows))
    promoted = 0
    for e in rows:
        st = db.get(Student, e.student_id)
        if st.status != "active":
            continue
        e.status = "promoted"
        e.end_date = max(e.start_date, body.effective_date - timedelta(days=1))
        _enroll(db, p, st, dst, body.effective_date, transferred_from=e.id, remarks=f"Promoted from {src.name}")
        promoted += 1
    audit.record(db, p, "batches", src.id, "promotion", new={"to_batch_id": dst.id, "students": promoted})
    db.commit()
    return {"promoted": promoted}


# ----------------------------------------------------------------------------- logins & parent links


class LoginIn(BaseModel):
    email: EmailStr
    password: str | None = Field(default=None, min_length=10, max_length=256)


def _create_login(db: Session, p: Principal, obj, role: str, body: LoginIn) -> dict:
    if obj.user_id:
        raise Conflict("A login already exists for this record")
    user, temp = create_user_account(db, p, body.email, obj.full_name, getattr(obj, "phone", None), body.password, role_codes=[role],
                                     branch_id=getattr(obj, "branch_id", None))
    obj.user_id = user.id
    if not obj.email:
        obj.email = body.email
    audit.record(db, p, obj.__tablename__, obj.id, "login_created", new={"user_id": user.id, "email": user.email})
    db.commit()
    return {"user_id": user.id, "email": user.email, "temporary_password": temp}


@router.post("/students/{student_id}/create-login")
def student_login(student_id: uuid.UUID, body: LoginIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    return _create_login(db, p, get_tenant_obj(db, p, Student, student_id, label="Student"), "student", body)


@router.post("/teachers/{teacher_id}/create-login")
def teacher_login(teacher_id: uuid.UUID, body: LoginIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    return _create_login(db, p, get_tenant_obj(db, p, Teacher, teacher_id, label="Teacher"), "teacher", body)


@router.post("/parents/{parent_id}/create-login")
def parent_login(parent_id: uuid.UUID, body: LoginIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    return _create_login(db, p, get_tenant_obj(db, p, Parent, parent_id, label="Parent"), "parent", body)


class LinkParentIn(BaseModel):
    parent_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    relation: str = Field(default="guardian", pattern="^(father|mother|guardian|other)$")
    is_primary: bool = False
    can_view_fees: bool = True
    can_view_academics: bool = True


@router.post("/students/{student_id}/parents", status_code=201)
def link_parent(student_id: uuid.UUID, body: LinkParentIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("parents.write"))):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    if body.parent_id:
        parent = get_tenant_obj(db, p, Parent, body.parent_id, label="Parent")
    else:
        if not body.full_name:
            raise ValidationFailed("Provide parent_id or full_name for a new parent")
        parent = None
        if body.phone:
            parent = db.scalar(select(Parent).where(Parent.institute_id == p.institute_id, Parent.phone == body.phone))
        if parent is None:
            parent = Parent(institute_id=p.institute_id, full_name=body.full_name, phone=body.phone, email=body.email,
                            created_by_id=p.user_id, updated_by_id=p.user_id)
            db.add(parent)
            db.flush()
    if db.scalar(select(StudentParent.id).where(StudentParent.student_id == s.id, StudentParent.parent_id == parent.id)):
        raise Conflict("Parent is already linked to this student")
    db.add(StudentParent(institute_id=p.institute_id, student_id=s.id, parent_id=parent.id, relation=body.relation,
                         is_primary=body.is_primary, can_view_fees=body.can_view_fees, can_view_academics=body.can_view_academics))
    audit.record(db, p, "students", s.id, "parent_linked", new={"parent_id": parent.id, "relation": body.relation})
    db.commit()
    return {"parent_id": parent.id}


# ----------------------------------------------------------------------------- photos, ID cards, certificates


def _photo_upload(db, p, obj, file: UploadFile, table: str):
    stored = storage.store_upload(p.institute_id, f"photos/{table}", file, allowed={"png", "jpg", "jpeg", "webp"})
    obj.photo_object_key = stored.object_key
    audit.record(db, p, table, obj.id, "photo_updated")
    db.commit()
    return {"ok": True}


def _photo_stream(obj):
    if not obj.photo_object_key:
        raise NotFound("No photo")
    ext = obj.photo_object_key.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    return StreamingResponse(storage.iter_object(obj.photo_object_key), media_type=mime, headers={"Cache-Control": "private, max-age=600"})


@router.post("/students/{student_id}/photo")
def student_photo_upload(student_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                         p: Principal = Depends(require_perm("students.write"))):
    return _photo_upload(db, p, get_tenant_obj(db, p, Student, student_id, label="Student"), file, "students")


@router.get("/students/{student_id}/photo")
def student_photo(student_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    return _photo_stream(_student(db, p, student_id))


@router.post("/teachers/{teacher_id}/photo")
def teacher_photo_upload(teacher_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
                         p: Principal = Depends(require_perm("teachers.write"))):
    return _photo_upload(db, p, get_tenant_obj(db, p, Teacher, teacher_id, label="Teacher"), file, "teachers")


@router.get("/teachers/{teacher_id}/photo")
def teacher_photo(teacher_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    return _photo_stream(get_tenant_obj(db, p, Teacher, teacher_id, label="Teacher"))


@router.get("/students/{student_id}/id-card.pdf")
def student_id_card(student_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _student(db, p, student_id)
    inst = db.get(Institute, p.institute_id)
    batches = db.scalars(select(Batch.name).join(StudentEnrollment, StudentEnrollment.batch_id == Batch.id)
                         .where(StudentEnrollment.student_id == s.id, StudentEnrollment.status == "active")).all()
    valid = date(date.today().year + (1 if date.today().month >= 4 else 0), 3, 31).strftime("%d-%m-%Y")
    audit.record(db, p, "students", s.id, "id_card_generated")
    db.commit()
    return file_response(pdf.id_card_pdf(inst, s, list(batches), valid), f"id-card-{s.student_code}.pdf", "application/pdf", inline=True)


@router.get("/students/{student_id}/certificate.pdf")
def student_certificate(
    student_id: uuid.UUID,
    kind: str = Query("bonafide", pattern="^(bonafide|completion|participation)$"),
    course_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    p: Principal = Depends(require_perm("students.write")),
):
    s = get_tenant_obj(db, p, Student, student_id, label="Student")
    inst = db.get(Institute, p.institute_id)
    number = numbering.next_number(db, p.institute_id, "certificate", "CERT")
    if kind == "completion":
        course = db.get(Course, course_id) if course_id else None
        if course is None:
            raise ValidationFailed("course_id is required for completion certificates")
        title, body = "Certificate of Completion", f"has successfully completed the course\n{course.name}"
    elif kind == "participation":
        title, body = "Certificate of Participation", "has actively participated in the programmes of the institute"
    else:
        title, body = "Bonafide Certificate", f"(Student ID {s.student_code}) is a bonafide student of this institute\nsince {s.admission_date.strftime('%d-%m-%Y')}"
    audit.record(db, p, "students", s.id, "certificate_issued", new={"kind": kind, "number": number})
    db.commit()
    return file_response(pdf.certificate_pdf(inst, s, title, body, number), f"{kind}-{s.student_code}.pdf", "application/pdf", inline=True)


# ----------------------------------------------------------------------------- teacher profile & HR


@router.get("/teachers/{teacher_id}/profile")
def teacher_profile(teacher_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    t = get_tenant_obj(db, p, Teacher, teacher_id, label="Teacher")
    is_self = p.teacher_id == t.id
    if not (p.can("teachers.read") or is_self):
        raise Forbidden("You cannot view this teacher profile")
    res = REGISTRY["teachers"]
    masked = mask_fields(p, res) - ({"phone", "email", "address", "compensation_amount", "payout_reference"} if is_self else set())
    data = serialize(t, masked)
    today = today_local(db, p.institute_id)
    month_start = today.replace(day=1)
    assignments = db.execute(
        select(TeacherAssignment, Batch.name, Subject.name)
        .join(Batch, Batch.id == TeacherAssignment.batch_id)
        .join(Subject, Subject.id == TeacherAssignment.subject_id)
        .where(TeacherAssignment.teacher_id == t.id)
        .order_by(TeacherAssignment.start_date.desc())
    ).all()
    schedules = db.execute(
        select(ClassSchedule, Batch.name, Subject.name)
        .join(Batch, Batch.id == ClassSchedule.batch_id)
        .join(Subject, Subject.id == ClassSchedule.subject_id)
        .where(ClassSchedule.teacher_id == t.id, ClassSchedule.is_active.is_(True))
        .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
    ).all()
    att = dict(db.execute(select(TeacherAttendance.status, func.count()).where(TeacherAttendance.teacher_id == t.id)
                          .group_by(TeacherAttendance.status)).all())
    scheduled_month = db.scalar(select(func.count()).where(ClassSession.scheduled_teacher_id == t.id,
                                                           ClassSession.session_date.between(month_start, today)))
    conducted = db.execute(
        select(func.count(), func.coalesce(func.sum(TeacherAttendance.teaching_minutes), 0))
        .join(ClassSession, ClassSession.id == TeacherAttendance.session_id)
        .where(TeacherAttendance.teacher_id == t.id, TeacherAttendance.status.in_(("present", "late")),
               ClassSession.session_date.between(month_start, today))
    ).one()
    substitute = db.scalar(select(func.count()).select_from(ClassSessionTeacher).join(ClassSession, ClassSession.id == ClassSessionTeacher.session_id)
                           .where(ClassSessionTeacher.teacher_id == t.id, ClassSessionTeacher.role == "substitute",
                                  ClassSession.session_date.between(month_start, today)))
    leaves = db.scalars(select(TeacherLeave).where(TeacherLeave.teacher_id == t.id).order_by(TeacherLeave.start_date.desc()).limit(30)).all()
    out = {
        "teacher": data,
        "assignments": [{"id": a.id, "batch": bn, "subject": sn, "role": a.role, "start_date": a.start_date, "end_date": a.end_date,
                         "is_active": a.is_active} for a, bn, sn in assignments],
        "timetable": [{"id": s.id, "day_of_week": s.day_of_week, "start_time": s.start_time, "end_time": s.end_time, "batch": bn,
                       "subject": sn} for s, bn, sn in schedules],
        "attendance": att,
        "workload_this_month": {"scheduled_sessions": scheduled_month, "conducted_sessions": conducted[0],
                                "teaching_hours": round(conducted[1] / 60, 1), "substitute_sessions": substitute},
        "leaves": [audit.snapshot(l) for l in leaves],
        "leave_balances": [audit.snapshot(b) for b in db.scalars(select(LeaveBalance).where(LeaveBalance.teacher_id == t.id))],
    }
    if p.can("payroll.read") or is_self:
        out["payslips"] = [{"id": s.id, "payslip_number": s.payslip_number, "net_amount": s.net_amount, "status": s.status,
                            "created_at": s.created_at} for s in db.scalars(select(Payslip).where(Payslip.teacher_id == t.id)
                                                                             .order_by(Payslip.created_at.desc()).limit(24))]
    if p.can("teachers.read"):
        out["employment_records"] = [audit.snapshot(r) for r in db.scalars(select(EmploymentRecord).where(EmploymentRecord.teacher_id == t.id)
                                                                           .order_by(EmploymentRecord.effective_date.desc()))]
        out["documents"] = [{"id": d.id, "title": d.title, "category": d.category, "original_filename": d.original_filename,
                             "version_number": d.version_number, "created_at": d.created_at}
                            for d in db.scalars(select(Document).where(Document.owner_type == "teacher", Document.owner_id == t.id,
                                                                       Document.is_archived.is_(False)))]
        out["timeline"] = [{"at": l.created_at, "action": l.action, "entity": l.entity_type, "actor": l.actor_email, "reason": l.reason}
                           for l in db.scalars(select(AuditLog).where(AuditLog.institute_id == p.institute_id, AuditLog.entity_id == t.id)
                                               .order_by(AuditLog.created_at.desc()).limit(100))]
    return out


class ExitIn(BaseModel):
    exit_date: date
    status: str = Field(pattern="^(resigned|terminated)$")
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/teachers/{teacher_id}/exit")
def teacher_exit(teacher_id: uuid.UUID, body: ExitIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("hr.write", "teachers.write"))):
    t = get_tenant_obj(db, p, Teacher, teacher_id, lock=True, label="Teacher")
    t.exit_date = body.exit_date
    t.exit_reason = body.reason
    t.employment_status = body.status
    db.execute(update(TeacherAssignment).where(TeacherAssignment.teacher_id == t.id, TeacherAssignment.is_active.is_(True))
               .values(is_active=False, end_date=body.exit_date))
    db.execute(update(ClassSchedule).where(ClassSchedule.teacher_id == t.id, ClassSchedule.is_active.is_(True),
                                           or_(ClassSchedule.effective_to.is_(None), ClassSchedule.effective_to > body.exit_date))
               .values(effective_to=body.exit_date))
    db.add(EmploymentRecord(institute_id=p.institute_id, teacher_id=t.id, event_type="exit", effective_date=body.exit_date,
                            details=body.reason, created_by_id=p.user_id))
    if t.user_id and body.exit_date <= date.today():
        db.execute(update(User).where(User.id == t.user_id).values(is_active=False))
    future = db.scalar(select(func.count()).where(ClassSession.scheduled_teacher_id == t.id, ClassSession.session_date > body.exit_date,
                                                  ClassSession.status == "scheduled"))
    audit.record(db, p, "teachers", t.id, "exit", new={"status": body.status, "exit_date": body.exit_date}, reason=body.reason)
    db.commit()
    return {"ok": True, "future_sessions_needing_reassignment": future}


class LeaveDecisionIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    remarks: str | None = Field(default=None, max_length=1000)


@router.post("/teacher-leaves/{leave_id}/decide")
def decide_leave(leave_id: uuid.UUID, body: LeaveDecisionIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("leaves.write"))):
    lv = get_tenant_obj(db, p, TeacherLeave, leave_id, lock=True, label="Leave request")
    if lv.status != "pending":
        raise Conflict("Only pending requests can be decided")
    lv.status = body.status
    lv.decided_by_id = p.user_id
    lv.decided_at = datetime.now(timezone.utc)
    lv.decision_remarks = body.remarks
    affected = 0
    if body.status == "approved":
        bal = db.scalar(select(LeaveBalance).where(LeaveBalance.teacher_id == lv.teacher_id, LeaveBalance.year == lv.start_date.year,
                                                   LeaveBalance.leave_type == lv.leave_type))
        if bal is None:
            bal = LeaveBalance(institute_id=p.institute_id, teacher_id=lv.teacher_id, year=lv.start_date.year, leave_type=lv.leave_type, allotted=0, used=0)
            db.add(bal)
        bal.used = (bal.used or 0) + lv.days
        sessions = db.scalars(select(ClassSession).where(ClassSession.scheduled_teacher_id == lv.teacher_id,
                                                         ClassSession.session_date.between(lv.start_date, lv.end_date),
                                                         ClassSession.status == "scheduled")).all()
        for s in sessions:
            s.remarks = ((s.remarks or "") + " | Scheduled teacher on approved leave — assign substitute").strip(" |")
            affected += 1
        if affected:
            notifications.notify(db, p.institute_id, notifications.staff_user_ids(db, p.institute_id), "leave_decision",
                                 "Substitute needed", f"{affected} class(es) need a substitute due to approved leave.",
                                 link="/timetable", dedupe_key=f"leave-sub:{lv.id}")
    teacher = db.get(Teacher, lv.teacher_id)
    notifications.notify(db, p.institute_id, [teacher.user_id], "leave_decision", f"Leave {body.status}",
                         f"Your {lv.leave_type} leave ({lv.start_date:%d-%m-%Y} to {lv.end_date:%d-%m-%Y}) was {body.status}.",
                         link="/r/teacher-leaves", dedupe_key=f"leave:{lv.id}:{body.status}")
    audit.record(db, p, "teacher_leaves", lv.id, f"leave_{body.status}", reason=body.remarks, branch_id=lv.branch_id)
    db.commit()
    return {"ok": True, "sessions_needing_substitute": affected}


@router.post("/teacher-leaves/{leave_id}/cancel")
def cancel_leave(leave_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    lv = get_tenant_obj(db, p, TeacherLeave, leave_id, lock=True, label="Leave request")
    if not (p.can("leaves.write") or (p.teacher_id and lv.teacher_id == p.teacher_id)):
        raise Forbidden("You cannot cancel this leave request")
    if lv.status != "pending":
        raise Conflict("Only pending requests can be cancelled")
    lv.status = "cancelled"
    audit.record(db, p, "teacher_leaves", lv.id, "leave_cancelled")
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- documents (versioned)

DOC_OWNERS = {
    "student": (Student, "students"),
    "teacher": (Teacher, "teachers"),
    "parent": (Parent, "parents"),
    "admission": (None, "admissions"),
    "expense": (None, "expenses"),
    "institute": (None, "settings"),
}


def _doc_perm(p: Principal, owner_type: str, write: bool) -> None:
    if owner_type not in DOC_OWNERS:
        raise ValidationFailed("Unsupported document owner type")
    module = DOC_OWNERS[owner_type][1]
    p.require(f"{module}.{'write' if write else 'read'}", f"documents.{'write' if write else 'read'}")


@router.post("/documents/upload", status_code=201)
def upload_document(
    owner_type: str = Form(...),
    owner_id: uuid.UUID = Form(...),
    category: str = Form("other", max_length=60),
    title: str | None = Form(None, max_length=255),
    is_sensitive: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    _doc_perm(p, owner_type, True)
    model = DOC_OWNERS[owner_type][0]
    branch_id = None
    if model is not None:
        owner = get_tenant_obj(db, p, model, owner_id, label=owner_type.title())
        branch_id = getattr(owner, "branch_id", None)
    stored = storage.store_upload(p.institute_id, f"documents/{owner_type}", file)
    doc = Document(institute_id=p.institute_id, branch_id=branch_id, owner_type=owner_type, owner_id=owner_id, category=category,
                   title=title or stored.original_filename, original_filename=stored.original_filename, object_key=stored.object_key,
                   mime_type=stored.mime_type, size_bytes=stored.size_bytes, checksum_sha256=stored.checksum_sha256, version_number=1,
                   is_sensitive=is_sensitive, created_by_id=p.user_id, updated_by_id=p.user_id)
    db.add(doc)
    db.flush()
    audit.record(db, p, "documents", doc.id, "upload", new={"owner_type": owner_type, "owner_id": owner_id, "file": stored.original_filename})
    db.commit()
    return {"id": doc.id}


@router.post("/documents/{doc_id}/versions", status_code=201)
def new_document_version(doc_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    prev = get_tenant_obj(db, p, Document, doc_id, lock=True, label="Document")
    _doc_perm(p, prev.owner_type, True)
    if prev.is_archived:
        raise Conflict("Only the current version can be superseded")
    stored = storage.store_upload(p.institute_id, f"documents/{prev.owner_type}", file)
    doc = Document(institute_id=p.institute_id, branch_id=prev.branch_id, owner_type=prev.owner_type, owner_id=prev.owner_id,
                   category=prev.category, title=prev.title, original_filename=stored.original_filename, object_key=stored.object_key,
                   mime_type=stored.mime_type, size_bytes=stored.size_bytes, checksum_sha256=stored.checksum_sha256,
                   version_number=prev.version_number + 1, previous_version_id=prev.id, is_sensitive=prev.is_sensitive,
                   created_by_id=p.user_id, updated_by_id=p.user_id)
    prev.is_archived = True
    prev.archived_at = datetime.now(timezone.utc)
    db.add(doc)
    db.flush()
    audit.record(db, p, "documents", doc.id, "new_version", new={"version": doc.version_number, "previous": prev.id})
    db.commit()
    return {"id": doc.id, "version_number": doc.version_number}


@router.get("/documents/by-owner/{owner_type}/{owner_id}")
def documents_by_owner(owner_type: str, owner_id: uuid.UUID, include_history: bool = False, db: Session = Depends(get_db),
                       p: Principal = Depends(get_principal)):
    _doc_perm(p, owner_type, False)
    q = select(Document).where(Document.institute_id == p.institute_id, Document.owner_type == owner_type, Document.owner_id == owner_id)
    if not include_history:
        q = q.where(Document.is_archived.is_(False))
    return [{"id": d.id, "title": d.title, "category": d.category, "original_filename": d.original_filename, "mime_type": d.mime_type,
             "size_bytes": d.size_bytes, "checksum_sha256": d.checksum_sha256, "version_number": d.version_number,
             "previous_version_id": d.previous_version_id, "is_archived": d.is_archived, "created_at": d.created_at}
            for d in db.scalars(q.order_by(Document.created_at.desc()))]


@router.get("/documents/{doc_id}/download-link")
def document_link(doc_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    d = get_tenant_obj(db, p, Document, doc_id, label="Document")
    _doc_perm(p, d.owner_type, False)
    if d.is_sensitive and not p.can("students.sensitive") and d.owner_type == "student":
        raise Forbidden("This document is restricted")
    return {"url": download_url(p, d.object_key, d.original_filename, d.mime_type, "document", d.id)}
