"""Audit log helper — writes to the audit_events collection."""
from __future__ import annotations

import structlog
from datetime import datetime, timezone
from typing import Optional
from fastapi import Request

from app.repositories import audit_repo

log = structlog.get_logger("forecastiq.audit")


async def log_event(
    action: str,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    request: Optional[Request] = None,
    metadata: Optional[dict] = None,
) -> None:
    ip = None
    user_agent = None
    if request is not None:
        try:
            ip = request.headers.get("x-forwarded-for") or (
                request.client.host if request.client else None
            )
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()
            user_agent = (request.headers.get("user-agent") or "")[:512]
        except Exception:
            pass

    try:
        await audit_repo.insert(
            {
                "user_id": user_id,
                "org_id": org_id,
                "action": action,
                "ip": ip,
                "user_agent": user_agent,
                "metadata": metadata,
                "occurred_at": datetime.now(timezone.utc),
            }
        )
    except Exception as e:
        log.warning("audit_log_write_failed", action=action, error=str(e))
