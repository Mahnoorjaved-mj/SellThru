"""Organization document access.

Minimal today — a single Default Organization that every user/document
belongs to. Full org CRUD, membership, and invites are built in the
admin/hardening phase.
"""
from __future__ import annotations

from bson import ObjectId

from app.repositories.base import ensure_default_org, organizations

ensure_default = ensure_default_org


async def find_by_id(org_id: str) -> dict | None:
    return await organizations().find_one({"_id": ObjectId(org_id)})


async def list_all() -> list[dict]:
    cursor = organizations().find({})
    return await cursor.to_list(length=1000)
