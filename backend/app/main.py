"""Sellthru FastAPI application factory.

Handles lifespan DB connectivity, CORS, rate limits, structured logging,
request ids, the standard error envelope, and API routing (legacy paths +
versioned /api/v1 paths).
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

# Force UTF-8 stdout/stderr for Windows console unicode logs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.db import close, connect
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.repositories.base import backfill_org_ids, ensure_default_org, ensure_indexes

configure_logging()
log = get_logger("forecastiq")

problems = settings.validate_for_boot()
if problems:
    for p in problems:
        log.error("config_invalid", problem=p)
    raise RuntimeError(
        "Refusing to start with invalid configuration:\n- " + "\n- ".join(problems)
    )

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    connect()
    try:
        default_org_id = await ensure_default_org()
        await backfill_org_ids(default_org_id)
        await ensure_indexes()
    except Exception as e:
        log.warning("db_bootstrap_failed", error=str(e))

    try:
        from app.jobs.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        log.warning("scheduler_start_failed", error=str(e))

    log.info("app_booted", app_name=settings.APP_NAME, version=settings.APP_VERSION)
    yield

    # ---- Shutdown ----
    try:
        from app.jobs.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    close()


app = FastAPI(title=f"{settings.APP_NAME} API", version=settings.APP_VERSION, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
# Every resource router is mounted twice: at its legacy path (unchanged,
# nothing breaks) and under /api/v1 (canonical going forward). The legacy
# mount is marked deprecated in the OpenAPI schema.
from app.routers import admin, alerts, auth, catalog, forecast, health, insights, sales

app.include_router(health.router)

app.include_router(auth.router, deprecated=True)
app.include_router(sales.router, prefix="/api", deprecated=True)
app.include_router(forecast.router, prefix="/api", deprecated=True)
app.include_router(insights.router, prefix="/api", deprecated=True)
app.include_router(catalog.router, prefix="/api", deprecated=True)
app.include_router(alerts.router, prefix="/api", deprecated=True)
app.include_router(admin.router, prefix="/api", deprecated=True)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/api/health", deprecated=True)
async def legacy_health():
    """Deprecated alias of /readyz, kept for existing tooling."""
    from app.routers.health import readiness
    return await readiness()
