"""Audit event document access (append-only)."""
from __future__ import annotations

from app.repositories.base import audit_events


async def insert(doc: dict) -> None:
    await audit_events().insert_one(doc)


async def list_by_org(org_id: str, limit: int = 200) -> list[dict]:
    cursor = audit_events().find({"org_id": org_id}).sort("occurred_at", -1)
    return await cursor.to_list(length=limit)
