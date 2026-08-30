"""User document access. Email is the global unique key (not org-scoped)."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId

from app.repositories.base import users


async def find_by_email(email: str) -> dict | None:
    return await users().find_one({"email": email})


async def find_by_id(user_id: str | ObjectId) -> dict | None:
    oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
    return await users().find_one({"_id": oid})


async def count_all() -> int:
    return await users().count_documents({})


async def count_by_org(org_id: str) -> int:
    return await users().count_documents({"org_id": org_id})


async def list_by_org(org_id: str, limit: int = 500) -> list[dict]:
    cursor = users().find({"org_id": org_id}).sort("created_at", -1)
    return await cursor.to_list(length=limit)


async def set_role(user_id: str, role: str, is_admin: bool) -> None:
    await users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role, "is_admin": is_admin, "updated_at": datetime.now(timezone.utc)}},
    )


async def set_suspended(user_id: str, is_suspended: bool) -> None:
    await users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_suspended": is_suspended, "updated_at": datetime.now(timezone.utc)}},
    )


async def insert_user(doc: dict) -> dict:
    res = await users().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def update_last_login(user_id: str) -> None:
    await users().update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )


async def update_fields(user_id: str, fields: dict) -> None:
    await users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}},
    )


async def update_password_hash(user_id: str, password_hash: str) -> None:
    await users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": password_hash, "updated_at": datetime.now(timezone.utc)}},
    )
