import time
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger, request_id_var

configure_logging()
log = get_logger("classflow")

import app.crud.resources  # noqa: E402,F401  (registers generic resources)
from app.api.v1 import (  # noqa: E402
    admin,
    admissions,
    auth,
    classes,
    communication,
    exams,
    files,
    finance,
    learning,
    operations,
    people,
    platform,
    reports,
)
from app.crud.engine import REGISTRY, build_router, integrity_message  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from app.services.storage import ensure_bucket

        ensure_bucket()
    except Exception as exc:  # noqa: BLE001
        log.warning("object storage not ready at startup", extra={"ctx": {"error": type(exc).__name__}})
    log.info("Institute Management API started", extra={"ctx": {"env": settings.APP_ENV}})
    yield
    from app.db.session import engine

    engine.dispose()
    log.info("Institute Management API stopped")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version="1.0.0",
    description="Coaching institute & education management ERP. All endpoints are under /api/v1.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Branch-Id", "X-Institute-Id", "Idempotency-Key", "X-API-Key"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(rid[:64])
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        request_id_var.reset(token)
        raise
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = rid[:64]
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/") and "Cache-Control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    if request.url.path.startswith("/api/docs"):
        response.headers.setdefault("Content-Security-Policy", "default-src 'self' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net")
    else:
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    log.info("request", extra={"ctx": {"method": request.method, "path": request.url.path, "status": response.status_code, "ms": elapsed}})
    request_id_var.reset(token)
    return response


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "request_id": request_id_var.get()}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return _error(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(x) for x in e.get("loc", [])[1:]), "message": e.get("msg")} for e in exc.errors()]
    return _error(422, "validation_failed", "Some fields are invalid", details)


@app.exception_handler(StarletteHTTPException)
async def http_handler(_request: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(IntegrityError)
async def integrity_handler(_request: Request, exc: IntegrityError):
    return _error(409, "conflict", integrity_message(exc))


@app.exception_handler(OperationalError)
async def db_down_handler(_request: Request, exc: OperationalError):
    log.error("database operational error", extra={"ctx": {"error": type(exc.orig).__name__ if exc.orig else "unknown"}})
    return _error(503, "service_unavailable", "The database is temporarily unavailable")


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception):
    log.exception("unhandled error")
    return _error(500, "internal_error", "An unexpected error occurred. Quote the request ID when contacting support.")


app.include_router(platform.health_router)

api = APIRouter(prefix="/api/v1")
# Workflow routers first so their static paths take precedence over generic /{id} routes.
for r in (auth.router, admin.router, files.router, people.router, classes.router, learning.router, exams.router, admissions.router,
          finance.router, finance.public_router, operations.router, communication.router, reports.router, platform.router):
    api.include_router(r)
for res in REGISTRY.values():
    api.include_router(build_router(res))
app.include_router(api)
