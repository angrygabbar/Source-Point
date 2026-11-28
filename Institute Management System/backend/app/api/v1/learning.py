import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.common import get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature
from app.api.v1.files import download_url
from app.core.errors import Conflict, Forbidden, IntegrationUnavailable, NotFound, ValidationFailed
from app.crud.engine import REGISTRY, base_query, read_mode
from app.db.session import get_db
from app.integrations import providers, registry
from app.models import (
    Assignment,
    AssignmentAttachment,
    AssignmentComment,
    AssignmentGrade,
    AssignmentTarget,
    Batch,
    ClassSession,
    DiscussionPost,
    DiscussionThread,
    Institute,
    LessonProgress,
    LmsLesson,
    LmsModule,
    Material,
    MaterialVersion,
    OnlineMeeting,
    Student,
    StudentEnrollment,
    Subject,
    Submission,
    SubmissionFile,
    SubmissionVersion,
    SyllabusChapter,
    SyllabusProgress,
    Teacher,
    User,
)
from app.services import audit, feature_flags, notifications, outbox, storage
from app.services.finance import q2

router = APIRouter(tags=["Learning"])


def _visible(db: Session, p: Principal, resource: str, obj_id: uuid.UUID):
    res = REGISTRY[resource]
    mode = read_mode(p, res)
    if mode is None:
        raise Forbidden(f"You cannot view {res.label}")
    obj = db.scalar(base_query(p, res, mode, include_archived=True).where(res.model.id == obj_id))
    if obj is None:
        raise NotFound(f"{res.label} not found")
    return obj, mode


def _quota_check(db: Session, p: Principal, incoming: int) -> None:
    inst = db.get(Institute, p.institute_id)
    used = (db.scalar(select(func.coalesce(func.sum(MaterialVersion.size_bytes), 0)).where(MaterialVersion.institute_id == p.institute_id)) or 0)
    if inst.storage_quota_mb and used + incoming > inst.storage_quota_mb * 1024 * 1024:
        raise Conflict("Storage quota exceeded. Archive old material or increase the quota.")


# ----------------------------------------------------------------------------- materials


@router.post("/materials/upload", status_code=201)
def upload_materials(
    title: str = Form(..., max_length=255),
    category: str = Form("notes"),
    visibility: str = Form("batch"),
    description: str | None = Form(None),
    batch_id: uuid.UUID | None = Form(None),
    subject_id: uuid.UUID | None = Form(None),
    course_id: uuid.UUID | None = Form(None),
    academic_year_id: uuid.UUID | None = Form(None),
    session_id: uuid.UUID | None = Form(None),
    syllabus_chapter_id: uuid.UUID | None = Form(None),
    tags: str | None = Form(None, max_length=500),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    p: Principal = Depends(require_feature("materials")),
):
    from app.models.learning import MATERIAL_CATEGORIES

    if category not in MATERIAL_CATEGORIES:
        raise ValidationFailed("Invalid category")
    if visibility not in ("staff_only", "batch", "selected", "institute"):
        raise ValidationFailed("Invalid visibility")
    if not (p.can("materials.write") or (p.can("materials.write_own") and batch_id and batch_id in p.batch_ids)):
        raise Forbidden("You can only upload material for your own batches")
    if len(files) > 20:
        raise ValidationFailed("Upload at most 20 files at a time")
    batch = get_tenant_obj(db, p, Batch, batch_id, label="Batch") if batch_id else None
    if subject_id:
        get_tenant_obj(db, p, Subject, subject_id, label="Subject")
    if session_id:
        get_tenant_obj(db, p, ClassSession, session_id, label="Session")
    created = []
    for f in files:
        data, filename, mime = storage.validate_and_read(f)
        _quota_check(db, p, len(data))
        stored = storage.put_bytes(p.institute_id, "materials", filename, data, mime)
        m = Material(institute_id=p.institute_id, branch_id=batch.branch_id if batch else p.selected_branch_id,
                     title=title if len(files) == 1 else f"{title} – {filename}", description=description, category=category,
                     academic_year_id=academic_year_id or (batch.academic_year_id if batch else None),
                     course_id=course_id or (batch.course_id if batch else None), batch_id=batch_id, subject_id=subject_id,
                     session_id=session_id, syllabus_chapter_id=syllabus_chapter_id, visibility=visibility, current_version=1,
                     tags=tags, created_by_id=p.user_id, updated_by_id=p.user_id)
        db.add(m)
        db.flush()
        db.add(MaterialVersion(institute_id=p.institute_id, material_id=m.id, version_number=1, original_filename=stored.original_filename,
                               object_key=stored.object_key, mime_type=stored.mime_type, size_bytes=stored.size_bytes,
                               checksum_sha256=stored.checksum_sha256, uploaded_by_id=p.user_id))
        audit.record(db, p, "materials", m.id, "upload", new={"title": m.title, "file": stored.original_filename}, branch_id=m.branch_id)
        if visibility != "staff_only":
            outbox.emit(db, p.institute_id, "material.uploaded", "material", m.id, {"title": m.title, "batch_id": batch_id},
                        dedupe_key=f"material.uploaded:{m.id}")
        created.append(m.id)
    db.commit()
    return {"ids": created}


@router.post("/materials/{mid}/versions", status_code=201)
def new_material_version(mid: uuid.UUID, change_note: str | None = Form(None, max_length=2000), file: UploadFile = File(...),
                         db: Session = Depends(get_db), p: Principal = Depends(require_feature("materials"))):
    m = get_tenant_obj(db, p, Material, mid, lock=True, label="Material")
    if not (p.can("materials.write") or (p.can("materials.write_own") and (m.created_by_id == p.user_id or m.batch_id in p.batch_ids))):
        raise Forbidden("You cannot update this material")
    if m.is_archived:
        raise Conflict("Archived material cannot receive new versions")
    data, filename, mime = storage.validate_and_read(file)
    _quota_check(db, p, len(data))
    stored = storage.put_bytes(p.institute_id, "materials", filename, data, mime)
    m.current_version += 1
    db.add(MaterialVersion(institute_id=p.institute_id, material_id=m.id, version_number=m.current_version, original_filename=stored.original_filename,
                           object_key=stored.object_key, mime_type=stored.mime_type, size_bytes=stored.size_bytes,
                           checksum_sha256=stored.checksum_sha256, change_note=change_note, uploaded_by_id=p.user_id))
    audit.record(db, p, "materials", m.id, "new_version", new={"version": m.current_version, "file": stored.original_filename}, reason=change_note)
    db.commit()
    return {"version_number": m.current_version}


@router.get("/materials/{mid}/versions")
def material_versions(mid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("materials"))):
    m, mode = _visible(db, p, "materials", mid)
    versions = db.scalars(select(MaterialVersion).where(MaterialVersion.material_id == m.id).order_by(MaterialVersion.version_number.desc())).all()
    names = dict(db.execute(select(User.id, User.full_name).where(User.id.in_({v.uploaded_by_id for v in versions if v.uploaded_by_id}))).all())
    prev = None
    out = []
    for v in reversed(versions):
        out.append({"id": v.id, "version_number": v.version_number, "original_filename": v.original_filename, "mime_type": v.mime_type,
                    "size_bytes": v.size_bytes, "checksum_sha256": v.checksum_sha256, "change_note": v.change_note,
                    "uploaded_by": names.get(v.uploaded_by_id), "created_at": v.created_at,
                    "comparison": None if prev is None else {
                        "size_delta_bytes": v.size_bytes - prev.size_bytes, "content_changed": v.checksum_sha256 != prev.checksum_sha256,
                        "type_changed": v.mime_type != prev.mime_type, "filename_changed": v.original_filename != prev.original_filename}})
        prev = v
    return list(reversed(out))


@router.get("/materials/{mid}/download-link")
def material_link(mid: uuid.UUID, version: int | None = None, db: Session = Depends(get_db), p: Principal = Depends(require_feature("materials"))):
    m, mode = _visible(db, p, "materials", mid)
    if m.is_archived and mode != "all":
        raise NotFound("Material not found")
    q = select(MaterialVersion).where(MaterialVersion.material_id == m.id)
    q = q.where(MaterialVersion.version_number == version) if version else q.order_by(MaterialVersion.version_number.desc())
    v = db.scalars(q.limit(1)).first()
    if v is None:
        raise NotFound("Version not found")
    return {"url": download_url(p, v.object_key, v.original_filename, v.mime_type, "material", m.id, v.id), "mime_type": v.mime_type}


# ----------------------------------------------------------------------------- assignments (teacher side)


def _assignment_for_write(db: Session, p: Principal, aid: uuid.UUID) -> Assignment:
    a = get_tenant_obj(db, p, Assignment, aid, lock=True, label="Assignment")
    if not (p.can("assignments.write") or (p.can("assignments.write_own") and (a.teacher_id == p.teacher_id or a.batch_id in p.batch_ids))):
        raise Forbidden("You cannot manage this assignment")
    return a


class TargetsIn(BaseModel):
    batch_ids: list[uuid.UUID] = []
    student_ids: list[uuid.UUID] = []


@router.put("/assignments/{aid}/targets")
def set_targets(aid: uuid.UUID, body: TargetsIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a = _assignment_for_write(db, p, aid)
    if a.status != "draft":
        raise Conflict("Targets can only be changed before publication")
    if not body.batch_ids and not body.student_ids:
        raise ValidationFailed("Select at least one batch or student")
    for b in body.batch_ids:
        get_tenant_obj(db, p, Batch, b, label="Batch")
        if not p.can("assignments.write") and b not in p.batch_ids:
            raise Forbidden("Multi-batch assignments are limited to your own batches")
    for s in body.student_ids:
        get_tenant_obj(db, p, Student, s, label="Student")
    db.execute(delete(AssignmentTarget).where(AssignmentTarget.assignment_id == a.id))
    for b in set(body.batch_ids):
        db.add(AssignmentTarget(institute_id=p.institute_id, assignment_id=a.id, batch_id=b))
    for s in set(body.student_ids):
        db.add(AssignmentTarget(institute_id=p.institute_id, assignment_id=a.id, student_id=s))
    a.target_type = "students" if body.student_ids and not body.batch_ids else ("multi_batch" if len(set(body.batch_ids)) > 1 else "batch")
    audit.record(db, p, "assignments", a.id, "targets_set", new=body.model_dump())
    db.commit()
    return {"ok": True}


@router.post("/assignments/{aid}/attachments", status_code=201)
def add_attachments(aid: uuid.UUID, files: list[UploadFile] = File(...), db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a = _assignment_for_write(db, p, aid)
    if a.status in ("closed",):
        raise Conflict("Closed assignments cannot be changed")
    ids = []
    for f in files[:10]:
        st = storage.store_upload(p.institute_id, "assignments", f)
        att = AssignmentAttachment(institute_id=p.institute_id, assignment_id=a.id, original_filename=st.original_filename, object_key=st.object_key,
                                   mime_type=st.mime_type, size_bytes=st.size_bytes, checksum_sha256=st.checksum_sha256, uploaded_by_id=p.user_id)
        db.add(att)
        db.flush()
        ids.append(att.id)
    audit.record(db, p, "assignments", a.id, "attachments_added", new={"count": len(ids)})
    db.commit()
    return {"ids": ids}


def _target_students(db: Session, a: Assignment) -> list[Student]:
    targets = db.scalars(select(AssignmentTarget).where(AssignmentTarget.assignment_id == a.id)).all()
    batch_ids = {t.batch_id for t in targets if t.batch_id} or ({a.batch_id} if not targets else set())
    student_ids = {t.student_id for t in targets if t.student_id}
    when = a.assigned_date
    q = select(Student).where(Student.institute_id == a.institute_id, Student.is_archived.is_(False))
    conds = []
    if batch_ids:
        conds.append(Student.id.in_(select(StudentEnrollment.student_id).where(
            StudentEnrollment.batch_id.in_(batch_ids), StudentEnrollment.start_date <= max(when, date.today()),
            or_(StudentEnrollment.end_date.is_(None), StudentEnrollment.end_date >= when))))
    if student_ids:
        conds.append(Student.id.in_(student_ids))
    return list(db.scalars(q.where(or_(*conds)).order_by(Student.full_name)).all()) if conds else []


@router.post("/assignments/{aid}/publish")
def publish(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a = _assignment_for_write(db, p, aid)
    if a.status != "draft":
        raise Conflict("Only draft assignments can be published")
    if a.due_at <= datetime.now(timezone.utc):
        raise ValidationFailed("Due date must be in the future")
    if not db.scalar(select(AssignmentTarget.id).where(AssignmentTarget.assignment_id == a.id)):
        db.add(AssignmentTarget(institute_id=p.institute_id, assignment_id=a.id, batch_id=a.batch_id))
        db.flush()
    a.status = "submission_open"
    a.published_at = datetime.now(timezone.utc)
    audit.record(db, p, "assignments", a.id, "publish", branch_id=a.branch_id)
    outbox.emit(db, p.institute_id, "assignment.published", "assignment", a.id, {"title": a.title}, dedupe_key=f"assignment.published:{a.id}")
    db.commit()
    return {"status": a.status}


class StatusIn(BaseModel):
    status: Literal["under_evaluation", "closed", "submission_open"]


@router.post("/assignments/{aid}/status")
def change_status(aid: uuid.UUID, body: StatusIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a = _assignment_for_write(db, p, aid)
    allowed = {
        "submission_open": {"under_evaluation"},
        "under_evaluation": {"closed", "submission_open"},
        "evaluated": {"closed", "submission_open"},
        "published": {"under_evaluation", "closed"},
    }
    if body.status not in allowed.get(a.status, set()):
        raise Conflict(f"Cannot move from {a.status} to {body.status}")
    old = a.status
    a.status = body.status
    if body.status == "closed":
        a.closed_at = datetime.now(timezone.utc)
    audit.record(db, p, "assignments", a.id, "status_change", {"status": old}, {"status": body.status})
    db.commit()
    return {"status": a.status}


@router.get("/assignments/{aid}/submissions")
def assignment_submissions(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a = get_tenant_obj(db, p, Assignment, aid, label="Assignment")
    if not (p.can("submissions.read") or a.teacher_id == p.teacher_id or (p.teacher_id and a.batch_id in p.batch_ids)):
        raise Forbidden("You cannot view submissions for this assignment")
    subs = {s.student_id: s for s in db.scalars(select(Submission).where(Submission.assignment_id == a.id))}
    grades = {g.submission_id: g for g in db.scalars(select(AssignmentGrade).where(
        AssignmentGrade.submission_id.in_([s.id for s in subs.values()] or [uuid.uuid4()]), AssignmentGrade.is_current.is_(True)))}
    rows = []
    for st in _target_students(db, a):
        s = subs.pop(st.id, None)
        g = grades.get(s.id) if s else None
        rows.append({"student_id": st.id, "student_code": st.student_code, "full_name": st.full_name, "submission_id": s.id if s else None,
                     "status": s.status if s else "not_submitted", "submitted_at": s.submitted_at if s else None,
                     "is_late": s.is_late if s else False, "version": s.current_version if s else 0,
                     "marks": g.marks if g else None, "penalty_applied": g.penalty_applied if g else None, "feedback": g.feedback if g else None})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    metrics = {
        "assigned": len(rows),
        "submitted": sum(1 for r in rows if r["status"] not in ("not_submitted", "draft")),
        "not_submitted": counts.get("not_submitted", 0) + counts.get("draft", 0),
        "late": sum(1 for r in rows if r["is_late"]),
        "pending_evaluation": counts.get("submitted", 0) + counts.get("late", 0) + counts.get("under_review", 0),
        "evaluated": counts.get("evaluated", 0),
    }
    return {"assignment_id": a.id, "max_marks": a.max_marks, "status": a.status, "metrics": metrics, "rows": rows}


@router.get("/assignments/{aid}/detail")
def assignment_detail(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a, mode = _visible(db, p, "assignments", aid)
    names = dict(db.execute(select(Subject.id, Subject.name).where(Subject.id == a.subject_id)).all())
    teacher = db.get(Teacher, a.teacher_id)
    out = {**audit.snapshot(a), "subject": names.get(a.subject_id), "teacher": teacher.full_name if teacher else None,
           "batch": db.scalar(select(Batch.name).where(Batch.id == a.batch_id)),
           "attachments": [{"id": x.id, "original_filename": x.original_filename, "size_bytes": x.size_bytes, "mime_type": x.mime_type}
                           for x in db.scalars(select(AssignmentAttachment).where(AssignmentAttachment.assignment_id == a.id))],
           "targets": [{"batch_id": t.batch_id, "student_id": t.student_id} for t in db.scalars(select(AssignmentTarget).where(AssignmentTarget.assignment_id == a.id))],
           "can_manage": p.can("assignments.write") or (p.can("assignments.write_own") and (a.teacher_id == p.teacher_id or a.batch_id in p.batch_ids))}
    if p.linked_student_ids and not p.teacher_id:
        mine = []
        for sid in p.linked_student_ids:
            s = db.scalar(select(Submission).where(Submission.assignment_id == a.id, Submission.student_id == sid))
            mine.append(_submission_out(db, s, sid) if s else {"student_id": sid, "status": "not_submitted", "versions": []})
        out["my_submissions"] = mine
    return out


def _submission_out(db: Session, s: Submission, student_id: uuid.UUID) -> dict:
    versions = db.scalars(select(SubmissionVersion).where(SubmissionVersion.submission_id == s.id).order_by(SubmissionVersion.version_number.desc())).all()
    files = db.scalars(select(SubmissionFile).where(SubmissionFile.submission_version_id.in_([v.id for v in versions] or [uuid.uuid4()]))).all()
    by_v: dict[uuid.UUID, list] = {}
    for f in files:
        by_v.setdefault(f.submission_version_id, []).append({"id": f.id, "original_filename": f.original_filename, "size_bytes": f.size_bytes})
    g = db.scalar(select(AssignmentGrade).where(AssignmentGrade.submission_id == s.id, AssignmentGrade.is_current.is_(True)))
    return {"id": s.id, "student_id": student_id, "status": s.status, "submitted_at": s.submitted_at, "is_late": s.is_late,
            "remarks": s.remarks, "grade": {"marks": g.marks, "penalty_applied": g.penalty_applied, "feedback": g.feedback, "graded_at": g.created_at} if g else None,
            "versions": [{"id": v.id, "version_number": v.version_number, "text_content": v.text_content, "remarks": v.remarks,
                          "is_final": v.is_final, "submitted_at": v.submitted_at, "is_late": v.is_late, "files": by_v.get(v.id, [])} for v in versions]}


@router.post("/assignments/{aid}/my-submission")
def save_my_submission(
    aid: uuid.UUID,
    submit: bool = Form(False),
    text_content: str | None = Form(None, max_length=50000),
    remarks: str | None = Form(None, max_length=2000),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    p: Principal = Depends(require_feature("homework")),
):
    if not p.student_id:
        raise Forbidden("Only students can submit their own homework")
    a, _ = _visible(db, p, "assignments", aid)
    if a.status not in ("submission_open", "published", "under_evaluation", "evaluated"):
        raise Conflict("This assignment is not accepting submissions")
    if a.submission_type == "offline":
        raise Conflict("This assignment is submitted offline")
    now = datetime.now(timezone.utc)
    late = now > a.due_at
    if late and (not a.allow_late or (a.late_until and now > a.late_until)):
        raise Conflict("The submission deadline has passed")
    sub = db.scalar(select(Submission).where(Submission.assignment_id == a.id, Submission.student_id == p.student_id).with_for_update())
    if sub is None:
        sub = Submission(institute_id=p.institute_id, assignment_id=a.id, student_id=p.student_id, status="draft", current_version=0)
        db.add(sub)
        db.flush()
    if sub.status == "evaluated" or (sub.status in ("submitted", "late", "under_review") and not a.allow_resubmission):
        raise Conflict("Already submitted. Resubmission is not permitted unless requested by the teacher.")
    draft = db.scalar(select(SubmissionVersion).where(SubmissionVersion.submission_id == sub.id, SubmissionVersion.is_final.is_(False))
                      .order_by(SubmissionVersion.version_number.desc()))
    if draft is None:
        sub.current_version += 1
        draft = SubmissionVersion(institute_id=p.institute_id, submission_id=sub.id, version_number=sub.current_version)
        db.add(draft)
        db.flush()
    if text_content is not None:
        draft.text_content = text_content
    if remarks is not None:
        draft.remarks = remarks
    for f in (files or [])[:10]:
        st = storage.store_upload(p.institute_id, "submissions", f)
        db.add(SubmissionFile(institute_id=p.institute_id, submission_version_id=draft.id, original_filename=st.original_filename,
                              object_key=st.object_key, mime_type=st.mime_type, size_bytes=st.size_bytes, checksum_sha256=st.checksum_sha256))
    db.flush()
    if submit:
        has_files = db.scalar(select(func.count()).where(SubmissionFile.submission_version_id == draft.id))
        if a.submission_type == "file" and not has_files:
            raise ValidationFailed("Attach at least one file")
        if a.submission_type == "text" and not (draft.text_content or "").strip():
            raise ValidationFailed("Enter your answer text")
        if a.submission_type == "file_or_text" and not has_files and not (draft.text_content or "").strip():
            raise ValidationFailed("Attach a file or enter text")
        draft.is_final = True
        draft.submitted_at = now
        draft.is_late = late
        sub.status = "late" if late else "submitted"
        sub.submitted_at = now
        sub.is_late = late
        sub.remarks = draft.remarks
        outbox.emit(db, p.institute_id, "submission.received", "submission", sub.id, {"assignment_id": a.id},
                    dedupe_key=f"submission.received:{sub.id}:{draft.version_number}")
    audit.record(db, p, "submissions", sub.id, "submit" if submit else "save_draft", new={"version": draft.version_number, "late": late})
    db.commit()
    return _submission_out(db, sub, p.student_id)


class GradeIn(BaseModel):
    marks: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    feedback: str | None = Field(default=None, max_length=10000)
    modification_reason: str | None = Field(default=None, max_length=1000)


@router.post("/submissions/{sid}/grade")
def grade_submission(sid: uuid.UUID, body: GradeIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    sub = get_tenant_obj(db, p, Submission, sid, lock=True, label="Submission")
    a = _assignment_for_write(db, p, sub.assignment_id)
    if sub.status in ("draft",):
        raise Conflict("Draft submissions cannot be graded")
    if body.marks > a.max_marks:
        raise ValidationFailed(f"Marks cannot exceed {a.max_marks}")
    current = db.scalar(select(AssignmentGrade).where(AssignmentGrade.submission_id == sub.id, AssignmentGrade.is_current.is_(True)))
    if current is not None:
        if a.status == "closed" and not p.can("grades.modify"):
            raise Forbidden("Modifying grades of a closed assignment requires grade-modification permission")
        if not body.modification_reason:
            raise ValidationFailed("A reason is required when changing an existing grade")
        current.is_current = False
        db.flush()
    penalty = q2(body.marks * a.late_penalty_percent / Decimal(100)) if sub.is_late and a.late_penalty_percent else Decimal("0")
    latest = db.scalar(select(SubmissionVersion.id).where(SubmissionVersion.submission_id == sub.id, SubmissionVersion.is_final.is_(True))
                       .order_by(SubmissionVersion.version_number.desc()))
    g = AssignmentGrade(institute_id=p.institute_id, submission_id=sub.id, submission_version_id=latest, marks=q2(body.marks - penalty),
                        penalty_applied=penalty, feedback=body.feedback, graded_by_id=p.user_id, is_current=True,
                        modification_reason=body.modification_reason)
    db.add(g)
    sub.status = "evaluated"
    db.flush()
    pending = db.scalar(select(func.count()).where(Submission.assignment_id == a.id, Submission.status.in_(("submitted", "late", "under_review"))))
    if pending == 0 and a.status == "under_evaluation":
        a.status = "evaluated"
    audit.record(db, p, "assignment_grades", g.id, "grade" if current is None else "regrade",
                 {"marks": current.marks} if current else None, {"marks": g.marks, "penalty": penalty}, body.modification_reason)
    outbox.emit(db, p.institute_id, "submission.evaluated", "submission", sub.id, {"assignment_id": a.id, "student_id": sub.student_id},
                dedupe_key=f"submission.evaluated:{g.id}")
    db.commit()
    return {"marks": g.marks, "penalty_applied": penalty}


class FeedbackIn(BaseModel):
    feedback: str = Field(min_length=3, max_length=5000)


@router.post("/submissions/{sid}/request-resubmission")
def request_resubmission(sid: uuid.UUID, body: FeedbackIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    sub = get_tenant_obj(db, p, Submission, sid, lock=True, label="Submission")
    a = _assignment_for_write(db, p, sub.assignment_id)
    if a.status == "closed":
        raise Conflict("Assignment is closed")
    sub.status = "resubmission_requested"
    db.add(AssignmentComment(institute_id=p.institute_id, assignment_id=a.id, submission_id=sub.id, author_id=p.user_id,
                             body=f"Resubmission requested: {body.feedback}"))
    st = db.get(Student, sub.student_id)
    notifications.notify(db, p.institute_id, notifications.student_and_parent_user_ids(db, [st.id]), "submission_evaluated",
                         f"Resubmission requested: {a.title}", body.feedback, link=f"/assignments/{a.id}", dedupe_key=f"resub:{sub.id}:{sub.current_version}")
    audit.record(db, p, "submissions", sub.id, "resubmission_requested", reason=body.feedback)
    db.commit()
    return {"ok": True}


@router.get("/submissions/{sid}")
def get_submission(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    sub, _ = _visible(db, p, "submissions", sid)
    return _submission_out(db, sub, sub.student_id)


@router.get("/submission-files/{fid}/download-link")
def submission_file_link(fid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    f = get_tenant_obj(db, p, SubmissionFile, fid, label="File")
    v = db.get(SubmissionVersion, f.submission_version_id)
    _visible(db, p, "submissions", v.submission_id)
    return {"url": download_url(p, f.object_key, f.original_filename, f.mime_type, "submission_file", f.id)}


@router.get("/assignment-attachments/{att_id}/download-link")
def attachment_link(att_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    att = get_tenant_obj(db, p, AssignmentAttachment, att_id, label="Attachment")
    _visible(db, p, "assignments", att.assignment_id)
    return {"url": download_url(p, att.object_key, att.original_filename, att.mime_type, "assignment_attachment", att.id)}


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    submission_id: uuid.UUID | None = None


@router.get("/assignments/{aid}/comments")
def list_comments(aid: uuid.UUID, submission_id: uuid.UUID | None = None, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a, mode = _visible(db, p, "assignments", aid)
    q = select(AssignmentComment, User.full_name).outerjoin(User, User.id == AssignmentComment.author_id).where(
        AssignmentComment.assignment_id == a.id, AssignmentComment.is_hidden.is_(False))
    if p.linked_student_ids and not p.teacher_id and not p.is_staff:
        own_subs = select(Submission.id).where(Submission.assignment_id == a.id, Submission.student_id.in_(p.linked_student_ids))
        q = q.where(or_(AssignmentComment.submission_id.is_(None), AssignmentComment.submission_id.in_(own_subs)))
    if submission_id:
        q = q.where(AssignmentComment.submission_id == submission_id)
    return [{"id": c.id, "body": c.body, "author": n, "submission_id": c.submission_id, "created_at": c.created_at}
            for c, n in db.execute(q.order_by(AssignmentComment.created_at)).all()]


@router.post("/assignments/{aid}/comments", status_code=201)
def add_comment(aid: uuid.UUID, body: CommentIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("homework"))):
    a, mode = _visible(db, p, "assignments", aid)
    if body.submission_id:
        sub = get_tenant_obj(db, p, Submission, body.submission_id, label="Submission")
        if sub.assignment_id != a.id:
            raise ValidationFailed("Submission does not belong to this assignment")
        if not p.teacher_id and not p.is_staff and sub.student_id not in p.linked_student_ids:
            raise Forbidden("You cannot comment on this submission")
    elif not (p.teacher_id or p.is_staff):
        raise Forbidden("Students comment on their own submission thread")
    c = AssignmentComment(institute_id=p.institute_id, assignment_id=a.id, submission_id=body.submission_id, author_id=p.user_id, body=body.body)
    db.add(c)
    db.commit()
    return {"id": c.id}


# ----------------------------------------------------------------------------- syllabus progress


@router.get("/syllabus/progress")
def syllabus_progress(batch_id: uuid.UUID | None = None, subject_id: uuid.UUID | None = None, teacher_id: uuid.UUID | None = None,
                      course_id: uuid.UUID | None = None, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    from app.models import BatchSubject, TeacherAssignment

    if not (p.can("syllabus.read") or p.can("syllabus.read_own")):
        raise Forbidden("You cannot view syllabus progress")
    q = select(BatchSubject.batch_id, BatchSubject.subject_id, Batch.name, Subject.name, Batch.course_id).join(
        Batch, Batch.id == BatchSubject.batch_id).join(Subject, Subject.id == BatchSubject.subject_id).where(
        BatchSubject.institute_id == p.institute_id, Batch.status == "active")
    if batch_id:
        q = q.where(BatchSubject.batch_id == batch_id)
    if subject_id:
        q = q.where(BatchSubject.subject_id == subject_id)
    if course_id:
        q = q.where(Batch.course_id == course_id)
    if teacher_id:
        q = q.where(BatchSubject.batch_id.in_(select(TeacherAssignment.batch_id).where(TeacherAssignment.teacher_id == teacher_id)))
    if not p.is_staff:
        q = q.where(BatchSubject.batch_id.in_(p.batch_ids or [uuid.uuid4()]))
    if p.branch_ids is not None:
        q = q.where(Batch.branch_id.in_(p.branch_ids))
    today = date.today()
    out = []
    for b_id, s_id, bname, sname, c_id in db.execute(q).all():
        chapters = db.scalars(select(SyllabusChapter.id).where(SyllabusChapter.subject_id == s_id,
                                                               or_(SyllabusChapter.course_id.is_(None), SyllabusChapter.course_id == c_id))).all()
        total = len(chapters)
        prog = db.execute(select(SyllabusProgress.status, SyllabusProgress.planned_end).where(
            SyllabusProgress.batch_id == b_id, SyllabusProgress.chapter_id.in_(chapters or [uuid.uuid4()]))).all()
        done = sum(1 for st, _ in prog if st == "completed")
        delayed = sum(1 for st, pe in prog if st != "completed" and pe and pe < today)
        out.append({"batch_id": b_id, "batch": bname, "subject_id": s_id, "subject": sname, "total_chapters": total, "completed": done,
                    "in_progress": sum(1 for st, _ in prog if st == "in_progress"), "delayed": delayed,
                    "coverage_percent": round(done * 100 / total, 1) if total else None})
    return out


# ----------------------------------------------------------------------------- LMS progress & discussions


class ProgressIn(BaseModel):
    progress_percent: int = Field(ge=0, le=100)


@router.post("/lms/lessons/{lid}/progress")
def lesson_progress(lid: uuid.UUID, body: ProgressIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    if not p.student_id:
        raise Forbidden("Only students record learning progress")
    lesson, _ = _visible(db, p, "lms-lessons", lid)
    row = db.scalar(select(LessonProgress).where(LessonProgress.lesson_id == lesson.id, LessonProgress.student_id == p.student_id).with_for_update())
    now = datetime.now(timezone.utc)
    if row is None:
        row = LessonProgress(institute_id=p.institute_id, lesson_id=lesson.id, student_id=p.student_id)
        db.add(row)
    row.progress_percent = max(row.progress_percent or 0, body.progress_percent)
    row.status = "completed" if row.progress_percent >= 100 else "in_progress"
    row.last_accessed_at = now
    if row.status == "completed" and not row.completed_at:
        row.completed_at = now
    db.commit()
    return {"status": row.status, "progress_percent": row.progress_percent}


@router.get("/lms/courses/{course_id}/outline")
def course_outline(course_id: uuid.UUID, student_id: uuid.UUID | None = None, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    if not (p.can("lms.read") or p.can("lms.read_own")):
        raise Forbidden("You cannot view LMS content")
    staff = p.is_staff or p.teacher_id
    mq = select(LmsModule).where(LmsModule.institute_id == p.institute_id, LmsModule.course_id == course_id)
    if not staff:
        mq = mq.where(LmsModule.is_published.is_(True))
    modules = db.scalars(mq.order_by(LmsModule.sequence)).all()
    sid = student_id if (student_id and (staff or student_id in p.linked_student_ids)) else p.student_id
    out = []
    for m in modules:
        lq = select(LmsLesson).where(LmsLesson.module_id == m.id)
        if not staff:
            lq = lq.where(LmsLesson.is_published.is_(True))
        lessons = db.scalars(lq.order_by(LmsLesson.sequence)).all()
        prog = {r.lesson_id: r for r in db.scalars(select(LessonProgress).where(LessonProgress.student_id == sid,
                                                                                  LessonProgress.lesson_id.in_([l.id for l in lessons] or [uuid.uuid4()])))} if sid else {}
        out.append({"id": m.id, "title": m.title, "description": m.description, "is_published": m.is_published,
                    "lessons": [{"id": l.id, "title": l.title, "lesson_type": l.lesson_type, "content": l.content, "video_url": l.video_url,
                                 "resource_url": l.resource_url, "material_id": l.material_id, "examination_id": l.examination_id,
                                 "duration_minutes": l.duration_minutes, "is_published": l.is_published,
                                 "progress": prog[l.id].progress_percent if l.id in prog else 0,
                                 "status": prog[l.id].status if l.id in prog else "not_started"} for l in lessons]})
    total = sum(len(m["lessons"]) for m in out)
    done = sum(1 for m in out for l in m["lessons"] if l["status"] == "completed")
    return {"modules": out, "total_lessons": total, "completed_lessons": done, "completion_percent": round(done * 100 / total, 1) if total else None}


class ThreadIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    batch_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    is_doubt: bool = False


@router.post("/discussions", status_code=201)
def create_thread(body: ThreadIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    if not (p.can("discussions.write") or p.can("discussions.write_own")):
        raise Forbidden("You cannot start discussions")
    if body.batch_id and not p.is_staff and body.batch_id not in p.batch_ids:
        raise Forbidden("You can only post in your own batches")
    t = DiscussionThread(institute_id=p.institute_id, author_id=p.user_id, **body.model_dump())
    db.add(t)
    db.commit()
    return {"id": t.id}


@router.get("/discussions/{tid}")
def get_thread(tid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    t, mode = _visible(db, p, "discussion-threads", tid)
    staff = p.is_staff or bool(p.teacher_id)
    q = select(DiscussionPost, User.full_name).outerjoin(User, User.id == DiscussionPost.author_id).where(DiscussionPost.thread_id == t.id)
    if not staff:
        q = q.where(DiscussionPost.is_hidden.is_(False))
    author = db.scalar(select(User.full_name).where(User.id == t.author_id))
    return {**audit.snapshot(t), "author": author, "can_moderate": staff,
            "posts": [{"id": x.id, "body": x.body, "author": n, "is_answer": x.is_answer, "is_hidden": x.is_hidden,
                       "report_count": x.report_count if staff else None, "created_at": x.created_at, "mine": x.author_id == p.user_id}
                      for x, n in db.execute(q.order_by(DiscussionPost.created_at)).all()]}


class PostIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


@router.post("/discussions/{tid}/posts", status_code=201)
def add_post(tid: uuid.UUID, body: PostIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    t, _ = _visible(db, p, "discussion-threads", tid)
    if t.is_locked:
        raise Conflict("Thread is locked")
    if not (p.can("discussions.write") or p.can("discussions.write_own")):
        raise Forbidden("You cannot reply")
    post = DiscussionPost(institute_id=p.institute_id, thread_id=t.id, author_id=p.user_id, body=body.body,
                          is_answer=bool(p.teacher_id or p.is_staff) and t.is_doubt)
    db.add(post)
    if t.author_id and t.author_id != p.user_id:
        notifications.notify(db, p.institute_id, [t.author_id], "message", f"New reply: {t.title}", body.body[:200], link=f"/discussions/{t.id}")
    db.commit()
    return {"id": post.id}


@router.post("/discussion-posts/{pid}/report")
def report_post(pid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    post = get_tenant_obj(db, p, DiscussionPost, pid, lock=True, label="Post")
    _visible(db, p, "discussion-threads", post.thread_id)
    post.report_count += 1
    if post.report_count >= 3:
        post.is_hidden = True
    audit.record(db, p, "discussion_posts", post.id, "reported")
    db.commit()
    return {"ok": True}


class ModerateIn(BaseModel):
    hide_post_id: uuid.UUID | None = None
    unhide_post_id: uuid.UUID | None = None
    is_locked: bool | None = None
    is_resolved: bool | None = None
    is_hidden: bool | None = None


@router.post("/discussions/{tid}/moderate")
def moderate(tid: uuid.UUID, body: ModerateIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    t = get_tenant_obj(db, p, DiscussionThread, tid, lock=True, label="Thread")
    is_author = t.author_id == p.user_id
    staff = p.is_staff or (p.teacher_id and (t.batch_id is None or t.batch_id in p.batch_ids))
    if not staff and not (is_author and body.is_resolved is not None and all(v is None for k, v in body.model_dump().items() if k != "is_resolved")):
        raise Forbidden("Only teachers or administrators can moderate")
    for pid, hidden in ((body.hide_post_id, True), (body.unhide_post_id, False)):
        if pid:
            post = get_tenant_obj(db, p, DiscussionPost, pid, label="Post")
            post.is_hidden = hidden
    for k in ("is_locked", "is_resolved", "is_hidden"):
        v = getattr(body, k)
        if v is not None:
            setattr(t, k, v)
    audit.record(db, p, "discussion_threads", t.id, "moderate", new=body.model_dump(exclude_none=True))
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- online meetings


class MeetingIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    start_at: datetime
    duration_minutes: int = Field(default=60, ge=10, le=600)
    provider: Literal["manual", "zoom", "google_meet"] = "manual"
    join_url: str | None = Field(default=None, max_length=1000)
    session_id: uuid.UUID | None = None


@router.post("/online-meetings", status_code=201)
def create_meeting(body: MeetingIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("lms"))):
    if not (p.can("lms.write") or p.can("lms.write_own")):
        raise Forbidden("You cannot create meetings")
    session = None
    if body.session_id:
        session = get_tenant_obj(db, p, ClassSession, body.session_id, lock=True, label="Session")
        if not p.can("lms.write") and session.batch_id not in p.batch_ids:
            raise Forbidden("You can only create meetings for your own classes")
    m = OnlineMeeting(institute_id=p.institute_id, session_id=body.session_id, provider=body.provider, title=body.title,
                      start_at=body.start_at, duration_minutes=body.duration_minutes, created_by_id=p.user_id)
    if body.provider == "manual":
        if not body.join_url or not body.join_url.startswith("https://"):
            raise ValidationFailed("Provide an https meeting link for manual meetings")
        m.join_url = body.join_url
    else:
        if not feature_flags.is_enabled(db, p.institute_id, "video_meetings"):
            raise IntegrationUnavailable("Video meeting integrations are disabled")
        cfg = registry.get_active(db, p.institute_id, "video")
        if cfg is None or cfg.provider != body.provider:
            raise IntegrationUnavailable(f"{body.provider} is not configured. Use a manual link or configure the integration.")
        inst = db.get(Institute, p.institute_id)
        try:
            fn = providers.zoom_create_meeting if body.provider == "zoom" else providers.google_meet_create
            res = fn(cfg, body.title, body.start_at, body.duration_minutes, inst.timezone)
        except providers.ProviderError as e:
            raise IntegrationUnavailable(str(e))
        m.join_url, m.host_url, m.external_id, m.provider_payload = res["join_url"], res["host_url"], res["external_id"], res["raw"]
    db.add(m)
    if session is not None:
        session.online_meeting_url = m.join_url
    db.flush()
    audit.record(db, p, "online_meetings", m.id, "create", new={"provider": m.provider, "session_id": body.session_id})
    db.commit()
    return {"id": m.id, "join_url": m.join_url}
