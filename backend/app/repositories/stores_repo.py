"""Store master data access."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId

from app.repositories.base import stores


async def upsert(org_id: str, store_id: str, fields: dict) -> None:
    now = datetime.now(timezone.utc)
    await stores().update_one(
        {"org_id": org_id, "store_id": store_id},
        {"$set": {**fields, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def list_all(org_id: str) -> list[dict]:
    cursor = stores().find({"org_id": org_id}).sort("store_id", 1)
    return await cursor.to_list(length=2000)


async def find_by_id(org_id: str, oid: str) -> dict | None:
    return await stores().find_one({"org_id": org_id, "_id": ObjectId(oid)})


async def update_fields(org_id: str, oid: str, fields: dict) -> None:
    await stores().update_one(
        {"org_id": org_id, "_id": ObjectId(oid)},
        {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}},
    )


async def delete(org_id: str, oid: str) -> None:
    await stores().delete_one({"org_id": org_id, "_id": ObjectId(oid)})
