"""Import batch (CSV upload history) document access."""
from __future__ import annotations

from bson import ObjectId

from app.repositories.base import imports


async def insert(org_id: str, doc: dict) -> dict:
    doc = dict(doc)
    doc["org_id"] = org_id
    res = await imports().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def find_by_id(org_id: str, import_id: str) -> dict | None:
    return await imports().find_one({"org_id": org_id, "_id": ObjectId(import_id)})


async def find_by_file_hash(org_id: str, file_hash: str) -> dict | None:
    return await imports().find_one({"org_id": org_id, "file_hash": file_hash})


async def list_recent(org_id: str, limit: int = 50) -> list[dict]:
    cursor = imports().find({"org_id": org_id}).sort("created_at", -1)
    return await cursor.to_list(length=limit)


async def mark_rows_imported(org_id: str, import_id: str, rows_imported: int) -> None:
    await imports().update_one(
        {"org_id": org_id, "_id": ObjectId(import_id)},
        {"$set": {"rows_imported": rows_imported}},
    )


async def mark_undone(org_id: str, import_id: str, rows_removed: int) -> None:
    from datetime import datetime, timezone

    await imports().update_one(
        {"org_id": org_id, "_id": ObjectId(import_id)},
        {"$set": {"status": "undone", "rows_removed": rows_removed, "undone_at": datetime.now(timezone.utc)}},
    )
