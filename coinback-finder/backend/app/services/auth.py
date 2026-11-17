from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime, timedelta

import bcrypt
import jwt

from app.config import Settings

_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds=12)).decode()


class PasswordPolicyError(ValueError):
    pass


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise PasswordPolicyError("Password must be at least 12 characters.")
    if len(password.encode()) > 72:
        raise PasswordPolicyError("Password must be at most 72 bytes.")


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], (password_hash or _DUMMY_HASH).encode()) and password_hash is not None
    except ValueError:
        return False


def create_session_token(user_id: uuid.UUID, settings: Settings, now: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.session_ttl_minutes)).timestamp()),
        "typ": "session",
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_session_token(token: str, settings: Settings) -> tuple[uuid.UUID, int] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require": ["sub", "exp", "iat"]})
        if payload.get("typ") != "session":
            return None
        return uuid.UUID(payload["sub"]), int(payload["iat"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None


class LoginRateLimiter:
    """In-process sliding window limiter keyed by client address."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            if len(self._hits) > 10000:
                self._hits = {k: v for k, v in self._hits.items() if v}
            return True
