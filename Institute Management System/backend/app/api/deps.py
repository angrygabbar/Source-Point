import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, ModuleDisabled, Unauthorized
from app.core.security import decode_token, sha256_hex
from app.db.session import get_db
from app.models import (
    ApiKey,
    Parent,
    Permission,
    Role,
    RolePermission,
    Student,
    StudentEnrollment,
    StudentParent,
    Teacher,
    TeacherAssignment,
    User,
    UserRole,
)
from app.services import feature_flags


@dataclass
class Principal:
    user: User | None
    institute_id: uuid.UUID
    permissions: frozenset[str]
    role_codes: frozenset[str]
    portal: str
    branch_ids: frozenset[uuid.UUID] | None  # None = all branches in institute
    selected_branch_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    linked_student_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    batch_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    ip_address: str | None = None
    user_agent: str | None = None
    is_superuser: bool = False
    api_key_id: uuid.UUID | None = None

    @property
    def user_id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None

    def can(self, perm: str) -> bool:
        if self.is_superuser or "*" in self.permissions:
            return True
        return perm in self.permissions

    def can_any(self, *perms: str) -> bool:
        return any(self.can(p) for p in perms)

    def require(self, *perms: str) -> None:
        if not self.can_any(*perms):
            raise Forbidden("You do not have permission to perform this action")

    def check_branch(self, branch_id: uuid.UUID | None) -> None:
        if branch_id is None or self.branch_ids is None:
            return
        if branch_id not in self.branch_ids:
            raise Forbidden("This record belongs to a branch outside your access")

    @property
    def is_staff(self) -> bool:
        return self.portal == "admin" or self.is_superuser

    def owns_student(self, student_id: uuid.UUID | None) -> bool:
        return student_id is not None and student_id in self.linked_student_ids


PORTAL_PRIORITY = {"admin": 0, "teacher": 1, "parent": 2, "student": 3}


def _load_principal(db: Session, user: User, institute_id: uuid.UUID, request: Request) -> Principal:
    rows = db.execute(
        select(Role.code, Role.portal, UserRole.branch_id, Permission.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .outerjoin(RolePermission, RolePermission.role_id == Role.id)
        .outerjoin(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == user.id, or_(Role.institute_id.is_(None), Role.institute_id == institute_id))
    ).all()
    perms: set[str] = set()
    roles: set[str] = set()
    portals: set[str] = set()
    branch_scoped: set[uuid.UUID] = set()
    has_global_role = False
    for role_code, portal, branch_id, perm_code in rows:
        roles.add(role_code)
        portals.add(portal)
        if perm_code:
            perms.add(perm_code)
        if branch_id is None:
            has_global_role = True
        else:
            branch_scoped.add(branch_id)

    portal = min(portals, key=lambda p: PORTAL_PRIORITY.get(p, 9)) if portals else "student"
    if user.is_superuser:
        portal = "admin"
    branch_ids = None if (has_global_role or user.is_superuser or not rows) else frozenset(branch_scoped)

    p = Principal(
        user=user,
        institute_id=institute_id,
        permissions=frozenset(perms),
        role_codes=frozenset(roles),
        portal=portal,
        branch_ids=branch_ids,
        is_superuser=bool(user.is_superuser),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    today = date.today()

    teacher = db.scalar(select(Teacher).where(Teacher.user_id == user.id, Teacher.institute_id == institute_id))
    if teacher:
        p.teacher_id = teacher.id
        p.batch_ids = frozenset(
            db.scalars(
                select(TeacherAssignment.batch_id).where(
                    TeacherAssignment.teacher_id == teacher.id,
                    TeacherAssignment.is_active.is_(True),
                    or_(TeacherAssignment.end_date.is_(None), TeacherAssignment.end_date >= today),
                )
            ).all()
        )

    student = db.scalar(select(Student).where(Student.user_id == user.id, Student.institute_id == institute_id))
    linked: set[uuid.UUID] = set()
    if student:
        p.student_id = student.id
        linked.add(student.id)
    parent = db.scalar(select(Parent).where(Parent.user_id == user.id, Parent.institute_id == institute_id))
    if parent:
        p.parent_id = parent.id
        linked.update(db.scalars(select(StudentParent.student_id).where(StudentParent.parent_id == parent.id)).all())
    p.linked_student_ids = frozenset(linked)
    if linked and not teacher:
        p.batch_ids = frozenset(
            db.scalars(
                select(StudentEnrollment.batch_id).where(
                    StudentEnrollment.student_id.in_(linked), StudentEnrollment.status == "active"
                )
            ).all()
        )

    selected = request.headers.get("x-branch-id")
    if selected:
        try:
            sel = uuid.UUID(selected)
            if p.branch_ids is None or sel in p.branch_ids:
                p.selected_branch_id = sel
        except ValueError:
            pass
    return p


def _api_key_principal(db: Session, raw_key: str, request: Request) -> Principal:
    key = db.scalar(select(ApiKey).where(ApiKey.key_hash == sha256_hex(raw_key)))
    now = datetime.now(timezone.utc)
    if not key or key.revoked_at or (key.expires_at and key.expires_at < now):
        raise Unauthorized("Invalid API key")
    key.last_used_at = now
    db.commit()
    return Principal(
        user=None,
        institute_id=key.institute_id,
        permissions=frozenset(key.scopes or []),
        role_codes=frozenset({"api_key"}),
        portal="admin",
        branch_ids=None,
        api_key_id=key.id,
        ip_address=request.client.host if request.client else None,
    )


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_institute_id: str | None = Header(default=None),
) -> Principal:
    cached = getattr(request.state, "principal", None)
    if cached is not None:
        return cached
    if x_api_key and not authorization:
        p = _api_key_principal(db, x_api_key, request)
        request.state.principal = p
        return p
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token, "access")
    except jwt.PyJWTError:
        raise Unauthorized("Session expired or invalid", code="token_invalid")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized("Account is inactive")
    institute_id = user.institute_id
    if user.is_superuser and x_institute_id:
        try:
            institute_id = uuid.UUID(x_institute_id)
        except ValueError:
            raise Unauthorized("Invalid institute header")
    if institute_id is None:
        raise Forbidden("No institute context. Platform administrators must select an institute.", code="no_institute")
    p = _load_principal(db, user, institute_id, request)
    request.state.principal = p
    return p


def require_perm(*perms: str):
    def dep(p: Principal = Depends(get_principal)) -> Principal:
        p.require(*perms)
        return p

    return dep


def require_feature(key: str):
    def dep(p: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> Principal:
        if not feature_flags.is_enabled(db, p.institute_id, key):
            raise ModuleDisabled(f"The '{key}' module is disabled for this institute")
        return p

    return dep
