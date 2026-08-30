"""Password reset token document access."""
from __future__ import annotations

from datetime import datetime
from bson import ObjectId

from app.repositories.base import reset_tokens


async def insert(doc: dict) -> None:
    await reset_tokens().insert_one(doc)


async def find_valid(token: str, now: datetime) -> dict | None:
    return await reset_tokens().find_one({"token": token, "used": False, "expires_at": {"$gt": now}})


async def mark_used(record_id: ObjectId) -> None:
    await reset_tokens().update_one({"_id": record_id}, {"$set": {"used": True}})
