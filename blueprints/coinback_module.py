"""SourcePoint gateway for the admin-only CoinBack Finder module."""

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

coinback_module_bp = Blueprint("coinback_module", __name__)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sourcepoint_token() -> str | None:
    secret = current_app.config.get("COINBACK_SSO_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        current_app.logger.error("COINBACK_SSO_SECRET must contain at least 32 bytes")
        return None

    issued_at = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": "sourcepoint",
        "aud": "coinback-finder",
        "sub": str(current_user.id),
        "sourcepoint_user_id": int(current_user.id),
        "username": current_user.username,
        "role": current_user.role,
        "iat": issued_at,
        "exp": issued_at + 120,
    }
    encoded_header = _encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_encode(signature)}"


def _access_error(api: bool):
    if not current_user.is_authenticated:
        if api:
            return jsonify({"error": {"code": 401, "message": "Sign in to SourcePoint to continue."}}), 401
        return redirect(url_for("auth.login_register", next=request.full_path))
    if (
        not current_user.is_active
        or not current_user.is_approved
        or current_user.role != UserRole.ADMIN.value
    ):
        if api:
            return jsonify({"error": {"code": 403, "message": "CoinBack Finder is available to SourcePoint administrators only."}}), 403
        return "CoinBack Finder is available to SourcePoint administrators only.", 403
    return None


def _query_target(base_url: str, upstream_path: str | None = None) -> str:
    target = f"{base_url.rstrip('/')}{upstream_path if upstream_path is not None else request.path}"
    if request.query_string:
        target = f"{target}?{request.query_string.decode('latin-1')}"
    return target


def _proxy(
    base_url: str,
    *,
    api: bool,
    upstream_path: str | None = None,
) -> Response | tuple[Response, int] | str | tuple[str, int]:
    denied = _access_error(api)
    if denied is not None:
        return denied

    headers = {}
    for name in ("Accept", "Content-Type", "Range", "If-None-Match", "If-Modified-Since", "X-Requested-With"):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    if api:
        token = _sourcepoint_token()
        if token is None:
            return jsonify({"error": {"code": 503, "message": "CoinBack SSO is not configured."}}), 503
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-Forwarded-Host"] = request.headers.get("X-Forwarded-Host", request.host)
        headers["X-Forwarded-Proto"] = request.headers.get("X-Forwarded-Proto", request.scheme)
        headers["X-Forwarded-Prefix"] = "/coinback"

    try:
        upstream = requests.request(
            method=request.method,
            url=_query_target(base_url, upstream_path),
            headers=headers,
            data=request.get_data(),
            timeout=(5, 120),
            allow_redirects=False,
        )
    except requests.RequestException:
        current_app.logger.exception("CoinBack upstream request failed")
        message = "CoinBack Finder is temporarily unavailable."
        if api:
            return jsonify({"error": {"code": 502, "message": message}}), 502
        return message, 502

    response_headers = {}
    for name in ("Content-Type", "Content-Disposition", "Cache-Control", "ETag", "Last-Modified", "Location"):
        value = upstream.headers.get(name)
        if value:
            response_headers[name] = value
    return Response(upstream.content, status=upstream.status_code, headers=response_headers)


@coinback_module_bp.route("/coinback", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
@coinback_module_bp.route("/coinback/", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
def home():
    frontend_url = current_app.config.get("COINBACK_FRONTEND_URL")
    if not frontend_url:
        return "CoinBack Finder frontend is not configured.", 503
    return _proxy(frontend_url, api=False)


@coinback_module_bp.route(
    "/coinback/<path:path>", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]
)
def frontend_path(path: str):
    frontend_url = current_app.config.get("COINBACK_FRONTEND_URL")
    if not frontend_url:
        return "CoinBack Finder frontend is not configured.", 503
    return _proxy(frontend_url, api=False)


@coinback_module_bp.route(
    "/coinback-api", defaults={"path": ""}, methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]
)
@coinback_module_bp.route(
    "/coinback-api/<path:path>", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]
)
def api_proxy(path: str):
    api_url = current_app.config.get("COINBACK_API_URL")
    if not api_url:
        return jsonify({"error": {"code": 503, "message": "CoinBack Finder API is not configured."}}), 503
    upstream_path = f"/{path}" if path else "/"
    return _proxy(api_url, api=True, upstream_path=upstream_path)
