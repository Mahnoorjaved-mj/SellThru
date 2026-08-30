"""Sales transaction document access.

Every function requires `org_id` as its first argument — there is no way to
query this collection without it. That makes a missing tenant scope a
TypeError at call time instead of a silent cross-org data leak.

Soft-deleted rows (is_deleted=True, set by "undo import") are excluded from
every query by default.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.repositories.base import sales


def _scoped(org_id: str, query: Optional[dict] = None, include_deleted: bool = False) -> dict:
    q = dict(query or {})
    q["org_id"] = org_id
    if not include_deleted:
        q["is_deleted"] = {"$ne": True}
    return q


async def count(org_id: str, query: Optional[dict] = None) -> int:
    return await sales().count_documents(_scoped(org_id, query))


async def insert_many(org_id: str, records: list[dict]) -> int:
    now = datetime.now(timezone.utc)
    for r in records:
        r["org_id"] = org_id
        r.setdefault("is_deleted", False)
        r.setdefault("created_at", now)
    if not records:
        return 0
    res = await sales().insert_many(records)
    return len(res.inserted_ids)


async def find_latest(org_id: str) -> dict | None:
    return await sales().find_one(_scoped(org_id), sort=[("date", -1)])


async def find_in_range(org_id: str, start: datetime, end: datetime, limit: int = 10000) -> list[dict]:
    cursor = sales().find(_scoped(org_id, {"date": {"$gte": start, "$lte": end}}))
    return await cursor.to_list(length=limit)


async def find_recent(org_id: str, limit: int = 10) -> list[dict]:
    cursor = sales().find(_scoped(org_id)).sort("date", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def find_paginated(org_id: str, query: dict, skip: int, limit: int) -> list[dict]:
    cursor = sales().find(_scoped(org_id, query)).sort("date", -1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


async def distinct_field(org_id: str, field: str) -> list:
    return await sales().distinct(field, _scoped(org_id))


async def aggregate(org_id: str, pipeline: list[dict], length: int = 1000) -> list[dict]:
    """Run an aggregation pipeline with an org_id + not-deleted $match prepended."""
    scoped_pipeline = [{"$match": _scoped(org_id)}] + pipeline
    return await sales().aggregate(scoped_pipeline).to_list(length=length)


async def find_existing_hashes(org_id: str, hashes: list[str]) -> set[str]:
    """Used for CSV-upload idempotency: which of these row hashes already exist for this org."""
    if not hashes:
        return set()
    cursor = sales().find(
        {"org_id": org_id, "row_hash": {"$in": hashes}}, {"row_hash": 1}
    )
    docs = await cursor.to_list(length=len(hashes))
    return {d["row_hash"] for d in docs}


async def soft_delete_by_import(org_id: str, import_id: str) -> int:
    """Undo an import: soft-delete every row it inserted. Returns rows affected."""
    res = await sales().update_many(
        {"org_id": org_id, "import_id": import_id, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc)}},
    )
    return res.modified_count
