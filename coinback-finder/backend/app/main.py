"""FastAPI application: `uvicorn app.main:app`."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api import (
    auth,
    dashboard,
    discovery,
    health,
    monitoring,
    notifications,
    offers,
    price_history,
    products,
    settings as settings_api,
    watchlist,
)
from app.api.deps import require_csrf_header
from app.config import get_settings
from app.database.session import SessionLocal
from app.services.bootstrap import ensure_defaults

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("coinback.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        with SessionLocal() as db:
            ensure_defaults(db)
    except Exception:
        logger.exception("Default bootstrap failed; check that migrations have been applied.")
    yield


app = FastAPI(
    title="CoinBack Finder API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Requested-With"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse({"error": {"code": exc.status_code, "message": str(exc.detail)}}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")), "message": err.get("msg", "Invalid value")}
        for err in exc.errors()
    ]
    message = "; ".join(f"{f['field']}: {f['message']}" if f["field"] else f["message"] for f in fields[:5])
    return JSONResponse({"error": {"code": 422, "message": message or "Invalid request.", "fields": fields}}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"error": {"code": 500, "message": "Internal server error."}}, status_code=500)


csrf = [Depends(require_csrf_header)]
for module in (auth, products, offers, monitoring, dashboard, discovery, notifications, watchlist, settings_api, price_history):
    app.include_router(module.router, dependencies=csrf)
app.include_router(health.router)
