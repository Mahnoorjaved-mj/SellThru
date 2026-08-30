"""TOTP 2FA secret document access."""
from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.base import twofa


async def upsert_secret(user_id: str, secret: str, recovery_code_hashes: list[str]) -> None:
    await twofa().update_one(
        {"user_id": user_id},
        {"$set": {
            "secret": secret,
            "enabled": False,
            "recovery_code_hashes": recovery_code_hashes,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def consume_recovery_code(user_id: str, code_hash: str) -> bool:
    res = await twofa().update_one(
        {"user_id": user_id, "recovery_code_hashes": code_hash},
        {"$pull": {"recovery_code_hashes": code_hash}},
    )
    return res.modified_count > 0


async def find_by_user(user_id: str) -> dict | None:
    return await twofa().find_one({"user_id": user_id})


async def mark_enabled(user_id: str) -> None:
    await twofa().update_one(
        {"user_id": user_id},
        {"$set": {"enabled": True, "verified_at": datetime.now(timezone.utc)}},
    )


async def delete_by_user(user_id: str) -> None:
    await twofa().delete_one({"user_id": user_id})
