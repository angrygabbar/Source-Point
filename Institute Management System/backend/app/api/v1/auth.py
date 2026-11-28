import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import Principal, _load_principal, get_principal
from app.core.config import settings
from app.core.errors import Forbidden, Unauthorized, ValidationFailed
from app.core.ratelimit import hit
from app.core.security import (
    constant_time_equals,
    create_access_token,
    decode_token,
    hash_password,
    new_opaque_token,
    password_needs_rehash,
    sha256_hex,
    validate_password_strength,
    verify_password,
)
from app.db.session import get_db
from app.integrations import registry
from app.models import (
    Branch,
    Institute,
    LoginHistory,
    NotificationDelivery,
    PasswordResetToken,
    RefreshToken,
    Student,
    User,
)
from app.services import audit, feature_flags

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE = "cf_refresh"
CSRF_COOKIE = "cf_csrf"
REUSE_GRACE_SECONDS = 20
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)




class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool = False


@router.post("/sourcepoint", response_model=TokenOut)
def sourcepoint_login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    """Exchange a short-lived SourcePoint identity token for an Institute session."""
    if not settings.SOURCEPOINT_SSO_SECRET or not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("SourcePoint sign-in is not configured", code="sso_unavailable")

    raw_token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(
            raw_token,
            settings.SOURCEPOINT_SSO_SECRET,
            algorithms=["HS256"],
            issuer="sourcepoint",
            audience="institute-management-system",
            options={"require": ["iss", "aud", "sub", "iat", "exp", "email"]},
            leeway=10,
        )
    except jwt.PyJWTError:
        raise Unauthorized("SourcePoint sign-in token is invalid or expired", code="sso_token_invalid")

    email = claims.get("email")
    if not isinstance(email, str) or not email.strip():
        raise Unauthorized("SourcePoint account has no email address", code="sso_email_missing")
    hit(f"sourcepoint-sso:{email.lower()}", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
    user = db.scalar(select(User).where(User.email.ilike(email.strip())))
    if not user or not user.is_active or not user.institute_id:
        raise Forbidden("No active Institute Management account matches this SourcePoint email", code="sso_account_unlinked")
    institute = db.get(Institute, user.institute_id)
    if institute is None or not institute.is_active:
        raise Forbidden("The institute account is inactive", code="sso_institute_inactive")

    now = datetime.now(timezone.utc)
    user.last_login_at = now
    ip, ua = _client(request)
    db.add(LoginHistory(
        user_id=user.id,
        institute_id=user.institute_id,
        email=email.strip().lower(),
        success=True,
        reason="sourcepoint_sso",
        ip_address=ip,
        user_agent=ua,
    ))
    raw_refresh, refresh_row = _issue_refresh(db, user, request)
    access_token, expires = create_access_token(user.id, user.institute_id, refresh_row.family_id)
    db.commit()
    _set_cookies(response, raw_refresh)
    return TokenOut(access_token=access_token, expires_in=expires, must_change_password=bool(user.must_change_password))


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=256)


class ProfileIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


def _client(request: Request) -> tuple[str | None, str]:
    return (request.client.host if request.client else None), request.headers.get("user-agent", "")[:500]


def _set_cookies(response: Response, refresh_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_DAYS * 86400
    response.set_cookie(
        REFRESH_COOKIE, refresh_token, max_age=max_age, httponly=True, secure=settings.COOKIE_SECURE,
        samesite="strict", path=settings.REFRESH_COOKIE_PATH,
    )
    response.set_cookie(
        CSRF_COOKIE, new_opaque_token()[:32], max_age=max_age, httponly=False, secure=settings.COOKIE_SECURE,
        samesite="strict", path="/",
    )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=settings.REFRESH_COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def _check_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not constant_time_equals(csrf_cookie, csrf_header):
        raise Forbidden("CSRF validation failed", code="csrf_failed")


def _issue_refresh(db: Session, user: User, request: Request, family: str | None = None) -> tuple[str, RefreshToken]:
    raw = new_opaque_token()
    ip, ua = _client(request)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=sha256_hex(raw),
        family_id=family or uuid.uuid4().hex,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        user_agent=ua,
        ip_address=ip,
    )
    db.add(rt)
    db.flush()
    return raw, rt


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip, ua = _client(request)
    email = body.email.lower().strip()
    hit(f"login:ip:{ip}", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
    hit(f"login:email:{email}", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
    user = db.scalar(select(User).where(User.email.ilike(email)))
    now = datetime.now(timezone.utc)

    def fail(reason: str, user_obj: User | None = None):
        db.add(LoginHistory(user_id=user_obj.id if user_obj else None, institute_id=user_obj.institute_id if user_obj else None,
                            email=email, success=False, reason=reason, ip_address=ip, user_agent=ua))
        db.commit()
        raise Unauthorized("Invalid email or password", code="invalid_credentials")

    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        fail("unknown_user")
    if user.locked_until and user.locked_until > now:
        db.add(LoginHistory(user_id=user.id, institute_id=user.institute_id, email=email, success=False, reason="locked", ip_address=ip, user_agent=ua))
        db.commit()
        raise Unauthorized("Account temporarily locked after repeated failures. Try again later.", code="account_locked")
    if not verify_password(body.password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.LOGIN_MAX_FAILURES:
            user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            user.failed_login_count = 0
        fail("bad_password", user)
    if not user.is_active:
        fail("inactive", user)
    if user.institute_id:
        inst = db.get(Institute, user.institute_id)
        if inst is None or not inst.is_active:
            fail("institute_inactive", user)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    raw, rt = _issue_refresh(db, user, request)
    token, expires = create_access_token(user.id, user.institute_id, rt.family_id)
    db.add(LoginHistory(user_id=user.id, institute_id=user.institute_id, email=email, success=True, reason="ok", ip_address=ip, user_agent=ua))
    db.commit()
    _set_cookies(response, raw)
    return TokenOut(access_token=token, expires_in=expires, must_change_password=bool(user.must_change_password))


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    cf_refresh: str | None = Cookie(default=None),
    cf_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
):
    _check_csrf(cf_csrf, x_csrf_token)
    if not cf_refresh:
        raise Unauthorized("No session", code="no_session")
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(cf_refresh)).with_for_update())
    now = datetime.now(timezone.utc)
    if rt is None:
        _clear_cookies(response)
        raise Unauthorized("Session not found", code="no_session")
    user = db.get(User, rt.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Account is inactive")
    if rt.revoked_at is not None:
        if rt.revoked_reason == "rotated" and (now - rt.revoked_at).total_seconds() < REUSE_GRACE_SECONDS:
            # Concurrent refresh from another tab: the rotated cookie is already set by the winning request.
            token, expires = create_access_token(user.id, user.institute_id, rt.family_id)
            return TokenOut(access_token=token, expires_in=expires, must_change_password=bool(user.must_change_password))
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, revoked_reason="reuse_detected")
        )
        audit.record(db, None, "users", user.id, "refresh_token_reuse", institute_id=user.institute_id)
        db.commit()
        _clear_cookies(response)
        raise Unauthorized("Session was revoked. Please sign in again.", code="session_revoked")
    if rt.expires_at < now:
        raise Unauthorized("Session expired", code="session_expired")
    raw, new_rt = _issue_refresh(db, user, request, rt.family_id)
    rt.revoked_at = now
    rt.revoked_reason = "rotated"
    rt.replaced_by_id = new_rt.id
    rt.last_used_at = now
    token, expires = create_access_token(user.id, user.institute_id, rt.family_id)
    db.commit()
    _set_cookies(response, raw)
    return TokenOut(access_token=token, expires_in=expires, must_change_password=bool(user.must_change_password))


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    cf_refresh: str | None = Cookie(default=None),
    cf_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
):
    _check_csrf(cf_csrf, x_csrf_token)
    if cf_refresh:
        rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(cf_refresh)))
        if rt:
            db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=datetime.now(timezone.utc), revoked_reason="logout")
            )
            db.commit()
    _clear_cookies(response)
    response.status_code = 204
    return response


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Authentication required")
    try:
        payload = decode_token(authorization.split(" ", 1)[1], "access")
    except jwt.PyJWTError:
        raise Unauthorized("Session expired or invalid", code="token_invalid")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized("Account is inactive")
    return user


@router.post("/logout-all", status_code=204)
def logout_all(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc), revoked_reason="logout_all")
    )
    db.commit()
    _clear_cookies(response)
    response.status_code = 204
    return response


@router.get("/me")
def me(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db),
       x_institute_id: str | None = Header(default=None)):
    institute_id = user.institute_id
    if user.is_superuser and x_institute_id:
        try:
            institute_id = uuid.UUID(x_institute_id)
        except ValueError:
            institute_id = user.institute_id
    base = {
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone,
            "is_superuser": user.is_superuser, "must_change_password": user.must_change_password,
            "last_login_at": user.last_login_at,
        }
    }
    if institute_id is None:
        institutes = db.scalars(select(Institute).order_by(Institute.name)).all() if user.is_superuser else []
        return {**base, "institute": None, "portal": "platform", "institutes": [{"id": i.id, "name": i.name} for i in institutes],
                "permissions": ["*"] if user.is_superuser else [], "roles": [], "branches": [], "features": {}}
    p = _load_principal(db, user, institute_id, request)
    inst = db.get(Institute, institute_id)
    bq = select(Branch).where(Branch.institute_id == institute_id, Branch.is_active.is_(True)).order_by(Branch.name)
    if p.branch_ids is not None:
        bq = bq.where(Branch.id.in_(p.branch_ids))
    branches = db.scalars(bq).all()
    linked = db.scalars(select(Student).where(Student.id.in_(p.linked_student_ids))).all() if p.linked_student_ids else []
    return {
        **base,
        "institute": {
            "id": inst.id, "name": inst.name, "code": inst.code, "has_logo": bool(inst.logo_object_key),
            "primary_color": inst.primary_color, "secondary_color": inst.secondary_color, "accent_color": inst.accent_color,
            "timezone": inst.timezone, "currency": inst.currency, "date_format": inst.date_format, "locale": inst.locale,
        },
        "portal": p.portal,
        "roles": sorted(p.role_codes),
        "permissions": sorted(p.permissions) if not p.is_superuser else ["*"],
        "branch_scoped": p.branch_ids is not None,
        "branches": [{"id": b.id, "name": b.name, "code": b.code} for b in branches],
        "student_id": p.student_id,
        "teacher_id": p.teacher_id,
        "parent_id": p.parent_id,
        "linked_students": [{"id": s.id, "full_name": s.full_name, "student_code": s.student_code, "branch_id": s.branch_id} for s in linked],
        "batch_ids": list(p.batch_ids),
        "features": feature_flags.get_flags(db, institute_id),
    }


@router.patch("/me")
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    before = audit.snapshot(user)
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    old, new = audit.diff(before, audit.snapshot(user))
    audit.record(db, None, "users", user.id, "profile_update", old, new, institute_id=user.institute_id)
    db.commit()
    return {"ok": True}


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    hit(f"chpw:{user.id}", 10, 300)
    if not verify_password(body.current_password, user.password_hash):
        raise ValidationFailed("Current password is incorrect")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise ValidationFailed(str(e))
    if verify_password(body.new_password, user.password_hash):
        raise ValidationFailed("New password must differ from the current password")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc), revoked_reason="password_change")
    )
    raw, _ = _issue_refresh(db, user, request)
    audit.record(db, None, "users", user.id, "password_change", institute_id=user.institute_id)
    db.commit()
    _set_cookies(response, raw)
    response.status_code = 204
    return response


def create_reset_token(db: Session, user: User, created_by_id: uuid.UUID | None = None) -> str:
    raw = new_opaque_token()
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=sha256_hex(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_MINUTES),
        created_by_id=created_by_id,
    ))
    return raw


@router.post("/forgot-password")
def forgot_password(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    ip, _ = _client(request)
    hit(f"forgot:{ip}", 5, 300)
    user = db.scalar(select(User).where(User.email.ilike(body.email.lower())))
    if user and user.is_active:
        email_cfg = registry.get_active(db, user.institute_id, "email")
        if email_cfg is not None:
            raw = create_reset_token(db, user)
            link = f"{settings.PUBLIC_BASE_URL}/reset-password?token={raw}"
            db.add(NotificationDelivery(
                institute_id=user.institute_id, user_id=user.id, channel="email", recipient=user.email,
                subject="Reset your ClassFlow password",
                body=f"Hello {user.full_name},\n\nUse this link within {settings.PASSWORD_RESET_MINUTES} minutes to reset your password:\n{link}\n\nIf you did not request this, ignore this email.",
                status="queued", scheduled_at=datetime.now(timezone.utc), next_attempt_at=datetime.now(timezone.utc),
            ))
        audit.record(db, None, "users", user.id, "password_reset_requested", institute_id=user.institute_id,
                     new={"email_channel": email_cfg is not None})
        db.commit()
    return {"message": "If the account exists and email delivery is configured, a reset link has been sent. "
                       "Otherwise contact your administrator for a reset link."}


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetIn, request: Request, db: Session = Depends(get_db)):
    ip, _ = _client(request)
    hit(f"reset:{ip}", 10, 300)
    rt = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == sha256_hex(body.token)).with_for_update())
    now = datetime.now(timezone.utc)
    if rt is None or rt.used_at is not None or rt.expires_at < now:
        raise ValidationFailed("Reset link is invalid or has expired")
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise ValidationFailed(str(e))
    user = db.get(User, rt.user_id)
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.password_changed_at = now
    user.failed_login_count = 0
    user.locked_until = None
    rt.used_at = now
    db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now, revoked_reason="password_reset")
    )
    audit.record(db, None, "users", user.id, "password_reset", institute_id=user.institute_id)
    db.commit()


@router.get("/sessions")
def sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
        .order_by(RefreshToken.created_at.desc())
    ).all()
    return [{"id": r.id, "created_at": r.created_at, "expires_at": r.expires_at, "ip_address": r.ip_address, "user_agent": r.user_agent} for r in rows]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(session_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rt = db.scalar(select(RefreshToken).where(RefreshToken.id == session_id, RefreshToken.user_id == user.id))
    if rt:
        db.execute(
            update(RefreshToken).where(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc), revoked_reason="user_revoked")
        )
        db.commit()
    return Response(status_code=204)


@router.get("/login-history")
def login_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(LoginHistory).where(LoginHistory.user_id == user.id).order_by(LoginHistory.created_at.desc()).limit(50)).all()
    return [{"created_at": r.created_at, "success": r.success, "reason": r.reason, "ip_address": r.ip_address, "user_agent": r.user_agent} for r in rows]


@router.get("/my-data")
def my_data_export(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Personal-data export for the signed-in user (data-protection request)."""
    data = {"user": audit.snapshot(user)}
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student:
        data["student_profile"] = audit.snapshot(student)
    data["login_history"] = [audit.snapshot(r) for r in db.scalars(select(LoginHistory).where(LoginHistory.user_id == user.id).limit(500))]
    audit.record(db, None, "users", user.id, "personal_data_export", institute_id=user.institute_id)
    db.commit()
    return data


@router.post("/request-account-closure", status_code=202)
def request_closure(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.closure_requested_at = datetime.now(timezone.utc)
    audit.record(db, None, "users", user.id, "account_closure_requested", institute_id=user.institute_id)
    db.commit()
    return {"message": "Account closure request recorded. An administrator will review it; statutory financial and academic records are retained."}
