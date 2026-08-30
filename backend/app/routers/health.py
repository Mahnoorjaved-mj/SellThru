"""Liveness/readiness probes."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness():
    """Process is up. Does not touch any dependency."""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness():
    """Process is up AND its dependencies (DB, scheduler) are reachable."""
    db_ok, db_error = False, None
    try:
        await get_db().command("ping")
        db_ok = True
    except Exception as e:
        db_error = str(e)

    scheduler_ok = False
    try:
        from app.jobs.scheduler import is_running
        scheduler_ok = is_running()
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok else "degraded",
        "db": {"ok": db_ok, "error": db_error},
        "scheduler": {"ok": scheduler_ok},
    }
