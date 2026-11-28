"""SourcePoint gateway for the standalone Institute Management System."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import requests
from flask import Blueprint, Response, current_app, jsonify, redirect, request, url_for
from flask_login import current_user

from enums import UserRole

institute_module_bp = Blueprint("institute_module", __name__)

_FRONTEND_PREFIX = "/institute"
_API_PREFIX = "/institute-api"
_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_ALLOWED_ROLES = {
    UserRole.ADMIN.value,
    UserRole.DEVELOPER.value,
    UserRole.TEACHER.value,
    UserRole.STUDENT.value,
}
_INSTITUTE_CSP = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'", "https://checkout.razorpay.com"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "font-src": ["'self'", "data:"],
    "connect-src": ["'self'", "https://lumberjack.razorpay.com"],
    "frame-src": ["'self'", "blob:", "https://api.razorpay.com", "https://checkout.razorpay.com"],
    "object-src": ["'self'", "blob:"],
    "media-src": ["'self'", "blob:"],
    "worker-src": ["'self'"],
    "manifest-src": ["'self'"],
    "frame-ancestors": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
}


def _is_api_request() -> bool:
    return request.path == _API_PREFIX or request.path.startswith(f"{_API_PREFIX}/")


def _is_public_webhook() -> bool:
    return request.path.startswith(f"{_API_PREFIX}/api/v1/webhooks/")


def _sourcepoint_token() -> str | None:
    secret = current_app.config.get("INSTITUTE_SSO_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        current_app.logger.error("INSTITUTE_SSO_SECRET must contain at least 32 bytes")
        return None

    issued_at = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": "sourcepoint",
        "aud": "institute-management-system",
        "sub": str(current_user.id),
        "sourcepoint_user_id": int(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "iat": issued_at,
        "exp": issued_at + 120,
    }

    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    signing_input = f"{encode(json.dumps(header, separators=(',', ':')).encode())}.{encode(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{encode(signature)}"


def _sso_redirect():
    token = _sourcepoint_token()
    if token is None:
        return "Institute Management System sign-in is not configured.", 503
    response = redirect(f"{_FRONTEND_PREFIX}/sso#{token}")
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _access_error():
    api_request = _is_api_request()
    if not current_user.is_authenticated:
        if api_request:
            return jsonify({"error": {"code": 401, "message": "Sign in to SourcePoint to continue."}}), 401
        return redirect(url_for("auth.login_register", next=request.full_path))

    if (
        not current_user.is_active
        or not current_user.is_approved
        or current_user.role not in _ALLOWED_ROLES
    ):
        message = "Institute Management System is available to SourcePoint administrators, teachers and students."
        if api_request:
            return jsonify({"error": {"code": 403, "message": message}}), 403
        return message, 403

    return None


def _target_url(base_url: str, upstream_path: str) -> str:
    target = f"{base_url.rstrip('/')}/{upstream_path.lstrip('/')}"
    if request.query_string:
        target = f"{target}?{request.query_string.decode('latin-1')}"
    return target


def _proxy(base_url: str | None, upstream_path: str, *, api_request: bool) -> Response | tuple[Response, int] | tuple[str, int]:
    denied = None if _is_public_webhook() else _access_error()
    if denied is not None:
        return denied
    if not base_url:
        message = "Institute Management System is not configured."
        if api_request:
            return jsonify({"error": {"code": 503, "message": message}}), 503
        return message, 503

    headers = {}
    for name in (
        "Accept",
        "Content-Type",
        "Range",
        "If-None-Match",
        "If-Modified-Since",
        "X-Requested-With",
        "X-CSRF-Token",
        "Authorization",
        "X-Razorpay-Signature",
    ):
        value = request.headers.get(name)
        if value:
            headers[name] = value

    if api_request:
        # Only forward this module's refresh and CSRF cookies to its own API.
        module_cookies = [
            f"{name}={request.cookies[name]}"
            for name in ("cf_refresh", "cf_csrf")
            if request.cookies.get(name)
        ]
        if module_cookies:
            headers["Cookie"] = "; ".join(module_cookies)

    prefix = _API_PREFIX if api_request else _FRONTEND_PREFIX
    headers.update(
        {
            "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", request.host),
            "X-Forwarded-Proto": request.headers.get("X-Forwarded-Proto", request.scheme),
            "X-Forwarded-Prefix": prefix,
        }
    )

    try:
        upstream = requests.request(
            method=request.method,
            url=_target_url(base_url, upstream_path),
            headers=headers,
            data=request.get_data(),
            timeout=(5, 120),
            allow_redirects=False,
        )
    except requests.RequestException:
        current_app.logger.exception("Institute Management System upstream request failed")
        message = "Institute Management System is temporarily unavailable."
        if api_request:
            return jsonify({"error": {"code": 502, "message": message}}), 502
        return message, 502

    response = Response(upstream.content, status=upstream.status_code)
    for name in ("Content-Type", "Content-Disposition", "Cache-Control", "ETag", "Last-Modified", "Location"):
        value = upstream.headers.get(name)
        if not value:
            continue
        if name == "Location" and value.startswith("/"):
            if api_request and value.startswith("/api/"):
                value = f"{_API_PREFIX}{value}"
            elif not api_request and value != _FRONTEND_PREFIX and not value.startswith(f"{_FRONTEND_PREFIX}/"):
                value = f"{_FRONTEND_PREFIX}{value}"
        response.headers[name] = value

    for cookie in upstream.raw.headers.getlist("Set-Cookie"):
        response.headers.add("Set-Cookie", cookie)

    if api_request:
        response.headers.setdefault("Cache-Control", "private, no-store")
    return response


@institute_module_bp.route(_FRONTEND_PREFIX, defaults={"path": ""}, methods=_METHODS)
@institute_module_bp.route(f"{_FRONTEND_PREFIX}/", defaults={"path": ""}, methods=_METHODS)
def home(path: str = ""):
    """Serve the Institute Management System beneath the SourcePoint URL."""
    denied = _access_error()
    if denied is not None:
        return denied
    if not request.cookies.get("cf_csrf"):
        return _sso_redirect()
    frontend_url = current_app.config.get("INSTITUTE_FRONTEND_URL")
    return _proxy(frontend_url, f"{_FRONTEND_PREFIX}/", api_request=False)


@institute_module_bp.route(f"{_FRONTEND_PREFIX}/<path:path>", methods=_METHODS)
def frontend_path(path: str):
    denied = _access_error()
    if denied is not None:
        return denied
    if path == "login" and request.args.get("local") != "1" and not request.cookies.get("cf_csrf"):
        return _sso_redirect()
    frontend_url = current_app.config.get("INSTITUTE_FRONTEND_URL")
    return _proxy(frontend_url, f"{_FRONTEND_PREFIX}/{path}", api_request=False)


@institute_module_bp.route(f"{_API_PREFIX}", defaults={"path": ""}, methods=_METHODS)
@institute_module_bp.route(f"{_API_PREFIX}/<path:path>", methods=_METHODS)
def api_proxy(path: str):
    api_url = current_app.config.get("INSTITUTE_API_URL")
    return _proxy(api_url, path, api_request=True)


# Flask-Talisman otherwise applies SourcePoint's main-site CSP to these proxied pages.
for _view in (home, frontend_path, api_proxy):
    _view.talisman_view_options = {"content_security_policy": _INSTITUTE_CSP}
