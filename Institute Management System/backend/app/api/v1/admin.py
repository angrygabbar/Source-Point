import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_perm
from app.api.v1.auth import create_reset_token, current_user
from app.core.config import settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import encrypt_secret, decrypt_secret, generate_temp_password, hash_password, new_opaque_token, sha256_hex
from app.crud.engine import REGISTRY, resource_meta
from app.db.session import get_db
from app.integrations.registry import PROVIDERS
from app.models import (
    ApiKey,
    Branch,
    Institute,
    IntegrationConfig,
    LoginHistory,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    SubscriptionPlan,
    TenantSubscription,
    User,
    UserRole,
    WebhookEndpoint,
)
from app.services import app_settings, audit, feature_flags, storage

router = APIRouter(tags=["Administration"])


# ----------------------------------------------------------------------------- metadata


@router.get("/meta/resources")
def meta_resources(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    out = []
    for res in REGISTRY.values():
        m = resource_meta(db, p, res)
        if m:
            out.append(m)
    return out


@router.get("/meta/resources/{name}")
def meta_resource(name: str, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    res = REGISTRY.get(name)
    if not res:
        raise NotFound("Unknown resource")
    m = resource_meta(db, p, res)
    if not m:
        raise Forbidden("Resource not available")
    return m


# ----------------------------------------------------------------------------- users & roles


class RoleAssignment(BaseModel):
    role_id: uuid.UUID
    branch_id: uuid.UUID | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=10, max_length=256)
    roles: list[RoleAssignment] = []
    default_branch_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    default_branch_id: uuid.UUID | None = None


def _user_out(db: Session, u: User) -> dict:
    roles = db.execute(
        select(Role.id, Role.code, Role.name, UserRole.branch_id).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == u.id)
    ).all()
    return {
        "id": u.id, "email": u.email, "full_name": u.full_name, "phone": u.phone, "is_active": u.is_active,
        "must_change_password": u.must_change_password, "last_login_at": u.last_login_at, "locked_until": u.locked_until,
        "created_at": u.created_at, "default_branch_id": u.default_branch_id, "closure_requested_at": u.closure_requested_at,
        "roles": [{"role_id": r[0], "code": r[1], "name": r[2], "branch_id": r[3]} for r in roles],
    }


def _role_perms(db: Session, role_id: uuid.UUID) -> set[str]:
    return set(
        db.scalars(select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id).where(RolePermission.role_id == role_id))
    )


def _assign_roles(db: Session, p: Principal, user: User, roles: list[RoleAssignment]) -> None:
    for ra in roles:
        role = db.scalar(select(Role).where(Role.id == ra.role_id, or_(Role.institute_id.is_(None), Role.institute_id == p.institute_id)))
        if role is None:
            raise ValidationFailed("Unknown role")
        if not (p.is_superuser or p.can("tenant.admin")):
            missing = _role_perms(db, role.id) - set(p.permissions)
            if missing:
                raise Forbidden(f"You cannot grant role '{role.name}' because it exceeds your own permissions")
        if ra.branch_id:
            br = db.scalar(select(Branch).where(Branch.id == ra.branch_id, Branch.institute_id == p.institute_id))
            if br is None:
                raise ValidationFailed("Unknown branch")
            p.check_branch(br.id)
        elif p.branch_ids is not None:
            raise Forbidden("Branch administrators can only grant branch-scoped roles")
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    for ra in roles:
        db.add(UserRole(user_id=user.id, role_id=ra.role_id, branch_id=ra.branch_id))


def create_user_account(db: Session, p: Principal, email: str, full_name: str, phone: str | None, password: str | None,
                        role_codes: list[str] | None = None, role_assignments: list[RoleAssignment] | None = None,
                        branch_id: uuid.UUID | None = None) -> tuple[User, str | None]:
    if db.scalar(select(User.id).where(func.lower(User.email) == email.lower())):
        raise Conflict("A user with this email already exists")
    temp = None
    if not password:
        temp = generate_temp_password()
        password = temp
    user = User(institute_id=p.institute_id, email=email.lower(), full_name=full_name, phone=phone,
                password_hash=hash_password(password), is_active=True, must_change_password=True, default_branch_id=branch_id)
    db.add(user)
    db.flush()
    assignments = list(role_assignments or [])
    for code in role_codes or []:
        role = db.scalar(select(Role).where(Role.code == code, or_(Role.institute_id.is_(None), Role.institute_id == p.institute_id)))
        if role:
            assignments.append(RoleAssignment(role_id=role.id, branch_id=branch_id if code not in ("student", "parent", "teacher") else None))
    _assign_roles(db, p, user, assignments)
    audit.record(db, p, "users", user.id, "create", new={"email": user.email, "roles": [str(a.role_id) for a in assignments]})
    return user, temp


@router.get("/users")
def list_users(
    q: str | None = Query(None, max_length=100),
    role: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
    p: Principal = Depends(require_perm("users.read")),
):
    query = select(User).where(User.institute_id == p.institute_id)
    if q:
        query = query.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    if role:
        query = query.where(User.id.in_(select(UserRole.user_id).join(Role, Role.id == UserRole.role_id).where(Role.code == role)))
    if p.branch_ids is not None:
        query = query.where(User.id.in_(select(UserRole.user_id).where(UserRole.branch_id.in_(p.branch_ids))))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [_user_out(db, u) for u in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/users", status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    user, temp = create_user_account(db, p, body.email, body.full_name, body.phone, body.password,
                                     role_assignments=body.roles, branch_id=body.default_branch_id)
    db.commit()
    return {**_user_out(db, user), "temporary_password": temp}


@router.get("/users/{user_id}")
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.read"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    return _user_out(db, u)


@router.patch("/users/{user_id}")
def update_user(user_id: uuid.UUID, body: UserUpdate, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    if u.id == p.user_id and body.is_active is False:
        raise ValidationFailed("You cannot deactivate your own account")
    before = audit.snapshot(u)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    if body.is_active is False:
        db.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(timezone.utc), revoked_reason="deactivated"))
    old, new = audit.diff(before, audit.snapshot(u))
    audit.record(db, p, "users", u.id, "update", old, new)
    db.commit()
    return _user_out(db, u)


@router.put("/users/{user_id}/roles")
def set_user_roles(user_id: uuid.UUID, roles: list[RoleAssignment], db: Session = Depends(get_db),
                   p: Principal = Depends(require_perm("roles.write", "users.write"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    before = [r["code"] for r in _user_out(db, u)["roles"]]
    _assign_roles(db, p, u, roles)
    db.flush()
    audit.record(db, p, "users", u.id, "roles_changed", {"roles": before}, {"roles": [r["code"] for r in _user_out(db, u)["roles"]]})
    db.commit()
    return _user_out(db, u)


@router.post("/users/{user_id}/reset-link")
def admin_reset_link(user_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    raw = create_reset_token(db, u, p.user_id)
    audit.record(db, p, "users", u.id, "reset_link_generated")
    db.commit()
    return {"reset_url": f"{settings.PUBLIC_BASE_URL}/reset-password?token={raw}", "expires_in_minutes": settings.PASSWORD_RESET_MINUTES}


@router.post("/users/{user_id}/unlock")
def unlock_user(user_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    u.locked_until = None
    u.failed_login_count = 0
    audit.record(db, p, "users", u.id, "unlock")
    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/revoke-sessions")
def revoke_user_sessions(user_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.write"))):
    u = db.scalar(select(User).where(User.id == user_id, User.institute_id == p.institute_id))
    if not u:
        raise NotFound("User not found")
    n = db.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(timezone.utc), revoked_reason="admin_revoked")).rowcount
    audit.record(db, p, "users", u.id, "sessions_revoked", new={"count": n})
    db.commit()
    return {"revoked": n}


@router.get("/users/{user_id}/login-history")
def user_login_history(user_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("users.read"))):
    rows = db.scalars(select(LoginHistory).where(LoginHistory.user_id == user_id, LoginHistory.institute_id == p.institute_id)
                      .order_by(LoginHistory.created_at.desc()).limit(100)).all()
    return [{"created_at": r.created_at, "success": r.success, "reason": r.reason, "ip_address": r.ip_address, "user_agent": r.user_agent} for r in rows]


@router.get("/login-history")
def institute_login_history(page: int = Query(1, ge=1), success: bool | None = None, db: Session = Depends(get_db),
                            p: Principal = Depends(require_perm("audit.read"))):
    q = select(LoginHistory).where(LoginHistory.institute_id == p.institute_id)
    if success is not None:
        q = q.where(LoginHistory.success.is_(success))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(LoginHistory.created_at.desc()).offset((page - 1) * 50).limit(50)).all()
    return {"items": [{"created_at": r.created_at, "email": r.email, "success": r.success, "reason": r.reason,
                       "ip_address": r.ip_address, "user_agent": r.user_agent} for r in rows], "total": total, "page": page, "page_size": 50}


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db), p: Principal = Depends(require_perm("roles.read"))):
    return [{"id": x.id, "code": x.code, "module": x.module, "description": x.description, "is_sensitive": x.is_sensitive}
            for x in db.scalars(select(Permission).order_by(Permission.module, Permission.code))]


class RoleIn(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,59}$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    portal: str = Field(default="admin", pattern="^(admin|teacher|student|parent)$")
    permissions: list[str] = []


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), p: Principal = Depends(require_perm("roles.read", "users.read"))):
    roles = db.scalars(select(Role).where(or_(Role.institute_id.is_(None), Role.institute_id == p.institute_id)).order_by(Role.name)).all()
    return [{"id": r.id, "code": r.code, "name": r.name, "description": r.description, "is_system": r.is_system,
             "portal": r.portal, "institute_id": r.institute_id, "permissions": sorted(_role_perms(db, r.id))} for r in roles]


def _set_role_perms(db: Session, p: Principal, role: Role, codes: list[str]) -> None:
    perms = db.scalars(select(Permission).where(Permission.code.in_(codes))).all()
    if len(perms) != len(set(codes)):
        raise ValidationFailed("Unknown permission code supplied")
    if not (p.is_superuser or p.can("tenant.admin")):
        over = set(codes) - set(p.permissions)
        if over:
            raise Forbidden("You cannot grant permissions you do not hold")
    if "platform.admin" in codes and not p.is_superuser:
        raise Forbidden("Platform permissions cannot be granted by institute administrators")
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for perm in perms:
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))


@router.post("/roles", status_code=201)
def create_role(body: RoleIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("roles.write"))):
    if db.scalar(select(Role.id).where(Role.code == body.code, or_(Role.institute_id.is_(None), Role.institute_id == p.institute_id))):
        raise Conflict("Role code already exists")
    role = Role(institute_id=p.institute_id, code=body.code, name=body.name, description=body.description, portal=body.portal, is_system=False)
    db.add(role)
    db.flush()
    _set_role_perms(db, p, role, body.permissions)
    audit.record(db, p, "roles", role.id, "create", new={"code": role.code, "permissions": body.permissions})
    db.commit()
    return {"id": role.id}


@router.put("/roles/{role_id}")
def update_role(role_id: uuid.UUID, body: RoleIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("roles.write"))):
    role = db.scalar(select(Role).where(Role.id == role_id, Role.institute_id == p.institute_id))
    if role is None:
        raise Forbidden("System roles cannot be modified; create a custom role instead")
    before = sorted(_role_perms(db, role.id))
    role.name, role.description, role.portal = body.name, body.description, body.portal
    _set_role_perms(db, p, role, body.permissions)
    audit.record(db, p, "roles", role.id, "update", {"permissions": before}, {"permissions": sorted(body.permissions)})
    db.commit()
    return {"id": role.id}


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("roles.delete"))):
    role = db.scalar(select(Role).where(Role.id == role_id, Role.institute_id == p.institute_id))
    if role is None:
        raise Forbidden("System roles cannot be deleted")
    if db.scalar(select(UserRole.id).where(UserRole.role_id == role.id).limit(1)):
        raise Conflict("Role is assigned to users; reassign them first")
    db.delete(role)
    audit.record(db, p, "roles", role_id, "delete")
    db.commit()


# ----------------------------------------------------------------------------- institute profile & branding


class InstituteUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=255)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    address: str | None = None
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    website: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    locale: str | None = Field(default=None, max_length=16)
    date_format: str | None = Field(default=None, max_length=20)
    tax_enabled: bool | None = None
    tax_label: str | None = Field(default=None, max_length=20)
    tax_rate: float | None = Field(default=None, ge=0, le=100)
    tax_registration_number: str | None = Field(default=None, max_length=30)
    invoice_prefix: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{1,10}$")
    receipt_prefix: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{1,10}$")
    financial_year_start_month: int | None = Field(default=None, ge=1, le=12)


def _inst_out(i: Institute) -> dict:
    d = audit.snapshot(i)
    d.pop("logo_object_key", None)
    d["has_logo"] = bool(i.logo_object_key)
    return d


@router.get("/institutes/current")
def get_institute(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    return _inst_out(db.get(Institute, p.institute_id))


@router.patch("/institutes/current")
def update_institute(body: InstituteUpdate, db: Session = Depends(get_db), p: Principal = Depends(require_perm("institutes.write", "tenant.admin"))):
    inst = db.get(Institute, p.institute_id)
    before = audit.snapshot(inst)
    values = body.model_dump(exclude_unset=True)
    if "timezone" in values:
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(values["timezone"])
        except Exception:  # noqa: BLE001
            raise ValidationFailed("Unknown timezone")
    for k, v in values.items():
        setattr(inst, k, v)
    old, new = audit.diff(before, audit.snapshot(inst))
    audit.record(db, p, "institutes", inst.id, "update", old, new)
    db.commit()
    return _inst_out(inst)


@router.post("/institutes/current/logo")
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db), p: Principal = Depends(require_perm("institutes.write", "tenant.admin"))):
    stored = storage.store_upload(p.institute_id, "branding", file, allowed={"png", "jpg", "jpeg", "webp"})
    inst = db.get(Institute, p.institute_id)
    inst.logo_object_key = stored.object_key
    audit.record(db, p, "institutes", inst.id, "logo_updated")
    db.commit()
    return {"ok": True}


@router.get("/institutes/current/logo")
def get_logo(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    inst = db.get(Institute, p.institute_id)
    if not inst.logo_object_key:
        raise NotFound("No logo configured")
    mime = "image/png" if inst.logo_object_key.endswith(".png") else "image/jpeg"
    if inst.logo_object_key.endswith(".webp"):
        mime = "image/webp"
    return StreamingResponse(storage.iter_object(inst.logo_object_key), media_type=mime, headers={"Cache-Control": "private, max-age=3600"})


# ----------------------------------------------------------------------------- settings & feature flags


@router.get("/settings/feature-flags")
def get_feature_flags(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    flags = feature_flags.get_flags(db, p.institute_id)
    return [{"key": k, "enabled": flags[k], "description": v[1]} for k, v in feature_flags.DEFAULT_FLAGS.items()]


@router.put("/settings/feature-flags")
def put_feature_flags(body: dict[str, bool], db: Session = Depends(get_db), p: Principal = Depends(require_perm("settings.write"))):
    before = feature_flags.get_flags(db, p.institute_id)
    for k, v in body.items():
        try:
            feature_flags.set_flag(db, p.institute_id, k, bool(v))
        except ValueError as e:
            raise ValidationFailed(str(e))
    audit.record(db, p, "feature_flags", None, "update", {k: before.get(k) for k in body}, body)
    db.commit()
    return feature_flags.get_flags(db, p.institute_id)


@router.get("/settings/app")
def get_app_settings(db: Session = Depends(get_db), p: Principal = Depends(require_perm("settings.read"))):
    return app_settings.get_all(db, p.institute_id)


@router.put("/settings/app")
def put_app_settings(body: dict[str, Any], db: Session = Depends(get_db), p: Principal = Depends(require_perm("settings.write"))):
    before = app_settings.get_all(db, p.institute_id)
    for k, v in body.items():
        try:
            app_settings.put(db, p.institute_id, k, v)
        except (ValueError, TypeError) as e:
            raise ValidationFailed(str(e))
    audit.record(db, p, "application_settings", None, "update", {k: before.get(k) for k in body}, body)
    db.commit()
    return app_settings.get_all(db, p.institute_id)


# ----------------------------------------------------------------------------- integrations


class IntegrationIn(BaseModel):
    is_enabled: bool = False
    config: dict[str, Any] = {}
    secrets: dict[str, str] = {}
    monthly_limit: int | None = Field(default=None, ge=0)


@router.get("/integrations")
def list_integrations(db: Session = Depends(get_db), p: Principal = Depends(require_perm("integrations.read"))):
    rows = {(r.provider_type, r.provider): r for r in db.scalars(select(IntegrationConfig).where(IntegrationConfig.institute_id == p.institute_id))}
    out = []
    for ptype, providers in PROVIDERS.items():
        for pname, spec in providers.items():
            r = rows.get((ptype, pname))
            secrets = json.loads(decrypt_secret(r.secrets_encrypted) or "{}") if r and r.secrets_encrypted else {}
            out.append({
                "provider_type": ptype, "provider": pname, "label": spec["label"],
                "config_fields": spec["config"], "secret_fields": spec["secrets"],
                "is_enabled": bool(r and r.is_enabled), "config": dict(r.config or {}) if r else {},
                "secrets_set": {k: bool(secrets.get(k)) for k in spec["secrets"]},
                "last_status": r.last_status if r else None, "last_error": r.last_error if r else None,
                "last_checked_at": r.last_checked_at if r else None, "monthly_limit": r.monthly_limit if r else None,
            })
    return out


@router.put("/integrations/{provider_type}/{provider}")
def put_integration(provider_type: str, provider: str, body: IntegrationIn, db: Session = Depends(get_db),
                    p: Principal = Depends(require_perm("integrations.write"))):
    spec = PROVIDERS.get(provider_type, {}).get(provider)
    if not spec:
        raise NotFound("Unknown provider")
    unknown = (set(body.config) - set(spec["config"])) | (set(body.secrets) - set(spec["secrets"]))
    if unknown:
        raise ValidationFailed(f"Unknown fields: {', '.join(sorted(unknown))}")
    row = db.scalar(select(IntegrationConfig).where(IntegrationConfig.institute_id == p.institute_id,
                                                    IntegrationConfig.provider_type == provider_type, IntegrationConfig.provider == provider))
    if row is None:
        row = IntegrationConfig(institute_id=p.institute_id, provider_type=provider_type, provider=provider, created_by_id=p.user_id)
        db.add(row)
    current = json.loads(decrypt_secret(row.secrets_encrypted) or "{}") if row.secrets_encrypted else {}
    for k, v in body.secrets.items():
        if v:
            current[k] = v
    if body.is_enabled:
        missing = [k for k in spec["config"] if k not in ("use_tls", "default_template", "template_language", "monthly_token_limit",
                                                         "input_cost_per_1k", "output_cost_per_1k", "base_url", "host_user",
                                                         "calendar_id", "sender_id", "username", "vapid_subject")
                   and not body.config.get(k)]
        missing += [k for k in spec["secrets"] if k not in ("webhook_secret",) and not current.get(k)]
        if missing:
            raise ValidationFailed(f"Cannot enable: missing {', '.join(missing)}")
        db.execute(update(IntegrationConfig).where(IntegrationConfig.institute_id == p.institute_id,
                                                   IntegrationConfig.provider_type == provider_type,
                                                   IntegrationConfig.provider != provider).values(is_enabled=False))
    row.config = body.config
    row.secrets_encrypted = encrypt_secret(json.dumps(current)) if current else None
    row.is_enabled = body.is_enabled
    row.monthly_limit = body.monthly_limit
    row.last_status = "configured" if body.is_enabled else "disabled"
    row.updated_by_id = p.user_id
    audit.record(db, p, "integration_configs", row.id, "configure",
                 new={"provider": f"{provider_type}/{provider}", "enabled": body.is_enabled, "secrets_updated": sorted(body.secrets)})
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- API keys


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(min_length=1)
    expires_in_days: int | None = Field(default=365, ge=1, le=1825)


@router.get("/api-keys")
def list_api_keys(db: Session = Depends(get_db), p: Principal = Depends(require_perm("webhooks.read"))):
    rows = db.scalars(select(ApiKey).where(ApiKey.institute_id == p.institute_id).order_by(ApiKey.created_at.desc())).all()
    return [{"id": k.id, "name": k.name, "key_prefix": k.key_prefix, "scopes": k.scopes, "last_used_at": k.last_used_at,
             "expires_at": k.expires_at, "revoked_at": k.revoked_at, "created_at": k.created_at} for k in rows]


@router.post("/api-keys", status_code=201)
def create_api_key(body: ApiKeyIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("webhooks.write"))):
    over = set(body.scopes) - set(p.permissions) if not p.is_superuser else set()
    if over:
        raise Forbidden("API key scopes cannot exceed your own permissions")
    raw = "cfk_" + new_opaque_token()
    key = ApiKey(institute_id=p.institute_id, name=body.name, key_prefix=raw[:12], key_hash=sha256_hex(raw), scopes=body.scopes,
                 expires_at=datetime.now(timezone.utc) + timedelta(days=body.expires_in_days) if body.expires_in_days else None,
                 created_by_id=p.user_id)
    db.add(key)
    db.flush()
    audit.record(db, p, "api_keys", key.id, "create", new={"name": body.name, "scopes": body.scopes})
    db.commit()
    return {"id": key.id, "api_key": raw, "note": "Store this key now; it will not be shown again."}


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("webhooks.write"))):
    key = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.institute_id == p.institute_id))
    if not key:
        raise NotFound("API key not found")
    key.revoked_at = datetime.now(timezone.utc)
    audit.record(db, p, "api_keys", key.id, "revoke")
    db.commit()


class WebhookSecretIn(BaseModel):
    secret: str = Field(min_length=16, max_length=256)


@router.put("/webhook-endpoints/{endpoint_id}/secret")
def set_webhook_secret(endpoint_id: uuid.UUID, body: WebhookSecretIn, db: Session = Depends(get_db),
                       p: Principal = Depends(require_perm("webhooks.write"))):
    ep = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.institute_id == p.institute_id))
    if not ep:
        raise NotFound("Webhook endpoint not found")
    ep.secret_encrypted = encrypt_secret(body.secret)
    audit.record(db, p, "webhook_endpoints", ep.id, "secret_updated")
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- platform (super administrator)


class InstituteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{2,50}$")
    admin_email: EmailStr
    admin_name: str = Field(min_length=2, max_length=200)
    branch_name: str = Field(default="Main Branch", max_length=200)
    plan_code: str | None = None


def _require_platform(user: User) -> None:
    if not user.is_superuser:
        raise Forbidden("Platform administrator access required")


@router.get("/platform/institutes")
def platform_institutes(db: Session = Depends(get_db), user: User = Depends(current_user)):
    _require_platform(user)
    return [{"id": i.id, "name": i.name, "code": i.code, "is_active": i.is_active, "created_at": i.created_at}
            for i in db.scalars(select(Institute).order_by(Institute.name))]


@router.post("/platform/institutes", status_code=201)
def platform_create_institute(body: InstituteCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _require_platform(user)
    from app.bootstrap import provision_institute

    inst, admin, temp = provision_institute(db, body.name, body.code, body.admin_email, body.admin_name, None, body.branch_name)
    if body.plan_code:
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == body.plan_code))
        if plan:
            db.add(TenantSubscription(institute_id=inst.id, plan_id=plan.id, status="trial",
                                      trial_ends_at=datetime.now(timezone.utc) + timedelta(days=plan.trial_days)))
    audit.record(db, None, "institutes", inst.id, "create", new={"code": inst.code, "by": user.email}, institute_id=inst.id)
    db.commit()
    return {"id": inst.id, "admin_email": admin.email, "temporary_password": temp}


@router.patch("/platform/institutes/{institute_id}")
def platform_toggle_institute(institute_id: uuid.UUID, is_active: bool, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _require_platform(user)
    inst = db.get(Institute, institute_id)
    if not inst:
        raise NotFound("Institute not found")
    inst.is_active = is_active
    audit.record(db, None, "institutes", inst.id, "activate" if is_active else "deactivate", new={"by": user.email}, institute_id=inst.id)
    db.commit()
    return {"ok": True}


class PlanIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    name: str = Field(max_length=120)
    description: str | None = None
    price_monthly: float = Field(ge=0)
    price_annual: float = Field(ge=0)
    max_students: int | None = None
    max_branches: int | None = None
    storage_quota_mb: int | None = None
    modules: list[str] = []
    trial_days: int = Field(default=14, ge=0, le=365)
    is_active: bool = True


@router.get("/platform/plans")
def list_plans(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [audit.snapshot(x) for x in db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.price_monthly))]


@router.post("/platform/plans", status_code=201)
def upsert_plan(body: PlanIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _require_platform(user)
    plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == body.code)) or SubscriptionPlan(code=body.code)
    for k, v in body.model_dump().items():
        setattr(plan, k, v)
    db.add(plan)
    db.commit()
    return audit.snapshot(plan)
