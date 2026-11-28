import uuid
from typing import Any

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal
from app.core.errors import Forbidden, NotFound
from app.models import ClassSession, ClassSessionTeacher, Student, StudentEnrollment


def get_tenant_obj(db: Session, p: Principal, model: type, obj_id: uuid.UUID, lock: bool = False, label: str | None = None) -> Any:
    q = select(model).where(model.id == obj_id)
    if hasattr(model, "institute_id"):
        q = q.where(model.institute_id == p.institute_id)
    if lock:
        q = q.with_for_update()
    obj = db.scalar(q)
    if obj is None:
        raise NotFound(f"{label or model.__name__} not found")
    if hasattr(obj, "branch_id") and obj.branch_id is not None:
        p.check_branch(obj.branch_id)
    return obj


def file_response(data: bytes, filename: str, mime: str, inline: bool = False) -> Response:
    disp = "inline" if inline else "attachment"
    safe = filename.replace('"', "")
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'{disp}; filename="{safe}"', "Cache-Control": "no-store"})


def ensure_student_access(db: Session, p: Principal, student: Student, require_staff_perm: str = "students.read") -> None:
    if p.can(require_staff_perm):
        p.check_branch(student.branch_id)
        return
    if p.owns_student(student.id):
        return
    if p.teacher_id and p.batch_ids:
        enrolled = db.scalar(
            select(StudentEnrollment.id).where(
                StudentEnrollment.student_id == student.id,
                StudentEnrollment.batch_id.in_(p.batch_ids),
                StudentEnrollment.status == "active",
            )
        )
        if enrolled:
            return
    raise Forbidden("You cannot access this student's records")


def teacher_can_handle_session(db: Session, p: Principal, s: ClassSession) -> bool:
    if not p.teacher_id:
        return False
    if s.scheduled_teacher_id == p.teacher_id or s.batch_id in p.batch_ids:
        return True
    return bool(
        db.scalar(select(ClassSessionTeacher.id).where(ClassSessionTeacher.session_id == s.id, ClassSessionTeacher.teacher_id == p.teacher_id))
    )


def ensure_session_access(db: Session, p: Principal, s: ClassSession, write: bool = False) -> None:
    perm = "sessions.write" if write else "sessions.read"
    if p.can(perm):
        p.check_branch(s.branch_id)
        return
    if teacher_can_handle_session(db, p, s):
        return
    if not write and s.batch_id in p.batch_ids:
        return
    raise Forbidden("You do not have access to this class session")
