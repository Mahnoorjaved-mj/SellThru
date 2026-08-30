"""OTP verification document access (signup email verification)."""
from __future__ import annotations

from datetime import datetime

from app.repositories.base import otp


async def count_recent(email: str, since: datetime) -> int:
    return await otp().count_documents({"email": email, "created_at": {"$gt": since}})


async def delete_by_email(email: str) -> None:
    await otp().delete_many({"email": email})


async def insert(doc: dict) -> None:
    await otp().insert_one(doc)


async def find_valid(email: str, code: str, now: datetime) -> dict | None:
    return await otp().find_one(
        {"email": email, "otp": code, "expires_at": {"$gt": now}},
        sort=[("_id", -1)],
    )
