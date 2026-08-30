"""Refresh-token session document access."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId

from app.repositories.base import sessions


async def insert(doc: dict) -> dict:
    doc = dict(doc)
    doc.setdefault("created_at", datetime.now(timezone.utc))
    doc.setdefault("revoked_at", None)
    res = await sessions().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def find_by_token_hash(token_hash: str) -> dict | None:
    return await sessions().find_one({"token_hash": token_hash})


async def revoke(session_id: str) -> None:
    await sessions().update_one(
        {"_id": ObjectId(session_id)}, {"$set": {"revoked_at": datetime.now(timezone.utc)}}
    )


async def revoke_all_for_user(user_id: str) -> None:
    await sessions().update_many(
        {"user_id": user_id, "revoked_at": None}, {"$set": {"revoked_at": datetime.now(timezone.utc)}}
    )


async def list_active_for_user(user_id: str) -> list[dict]:
    cursor = sessions().find({"user_id": user_id, "revoked_at": None}).sort("created_at", -1)
    return await cursor.to_list(length=50)


async def find_by_id_for_user(session_id: str, user_id: str) -> dict | None:
    return await sessions().find_one({"_id": ObjectId(session_id), "user_id": user_id})
