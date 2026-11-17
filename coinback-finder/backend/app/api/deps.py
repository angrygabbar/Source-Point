from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Query, Request, status
from jwt import InvalidTokenError
from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models import User
from app.database.session import get_db

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "coinback"


def require_csrf_header(request: Request) -> None:
    """Defence in depth alongside SameSite=Strict cookies: browsers cannot add this header cross-site without CORS."""
    if request.method in UNSAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid request header.")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "SourcePoint admin authentication required.")

    try:
        claims = jwt.decode(
            authorization[7:],
            settings.coinback_sso_secret,
            algorithms=["HS256"],
            issuer="sourcepoint",
            audience="coinback-finder",
        )
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "SourcePoint admin authentication required.") from exc

    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required.")
    try:
        sourcepoint_user_id = int(claims["sourcepoint_user_id"])
        username = str(claims["username"]).strip()[:100]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SourcePoint identity.") from exc
    if sourcepoint_user_id <= 0 or not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid SourcePoint identity.")

    user = db.scalar(select(User).where(User.sourcepoint_user_id == sourcepoint_user_id))
    if user is None:
        # Reuse an existing CoinBack profile with the same username when upgrading
        # old data, otherwise create a shadow row for CoinBack's own user relations.
        user = db.scalar(
            select(User).where(
                User.username == username,
                User.sourcepoint_user_id.is_(None),
            ).limit(1).with_for_update()
        )
        if user is not None:
            user.sourcepoint_user_id = sourcepoint_user_id
            user.is_active = True
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        else:
            statement = (
                pg_insert(User)
                .values(
                    username=username,
                    sourcepoint_user_id=sourcepoint_user_id,
                    is_active=True,
                )
                .on_conflict_do_nothing(index_elements=[User.sourcepoint_user_id])
            )
            db.execute(statement)
            db.commit()
        user = db.scalar(select(User).where(User.sourcepoint_user_id == sourcepoint_user_id))

    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "SourcePoint admin account is unavailable.")
    return user


@dataclass
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(50, ge=1, le=200),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def paginate(db: Session, stmt: Select, params: PageParams) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset(params.offset).limit(params.page_size)).all()
    return rows, total


def page_response(data: list[Any], total: int, params: PageParams) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "page": params.page,
            "page_size": params.page_size,
            "total": total,
            "pages": max(1, math.ceil(total / params.page_size)) if params.page_size else 1,
        },
    }


def like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def csv_list(value: str | None, allowed: set[str] | None = None) -> list[str]:
    if not value:
        return []
    items = [v.strip().upper() for v in value.split(",") if v.strip()]
    return [v for v in items if allowed is None or v in allowed]
