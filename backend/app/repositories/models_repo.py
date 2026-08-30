"""Trained-model record access (metadata only; artifacts live on disk)."""
from __future__ import annotations

from bson import ObjectId

from app.repositories.base import models


async def insert(org_id: str, doc: dict) -> dict:
    doc = dict(doc)
    doc["org_id"] = org_id
    res = await models().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def find_active(org_id: str) -> dict | None:
    return await models().find_one({"org_id": org_id, "status": "active"}, sort=[("trained_at", -1)])


async def find_by_id(org_id: str, model_oid: str) -> dict | None:
    return await models().find_one({"org_id": org_id, "_id": ObjectId(model_oid)})


async def list_recent(org_id: str, limit: int = 50) -> list[dict]:
    cursor = models().find({"org_id": org_id}).sort("trained_at", -1)
    return await cursor.to_list(length=limit)


async def archive_all(org_id: str) -> None:
    """Demote every currently-active model to archived (used before promoting a new one)."""
    await models().update_many({"org_id": org_id, "status": "active"}, {"$set": {"status": "archived"}})


async def promote(org_id: str, model_oid: str) -> None:
    await archive_all(org_id)
    await models().update_one({"org_id": org_id, "_id": ObjectId(model_oid)}, {"$set": {"status": "active"}})
