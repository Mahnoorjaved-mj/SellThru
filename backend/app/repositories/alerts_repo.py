"""Alert rules and notifications document access."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId

from app.repositories.base import alert_rules, notifications


async def insert_rule(org_id: str, doc: dict) -> dict:
    doc = dict(doc)
    doc["org_id"] = org_id
    doc.setdefault("enabled", True)
    doc.setdefault("created_at", datetime.now(timezone.utc))
    res = await alert_rules().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def list_rules(org_id: str) -> list[dict]:
    cursor = alert_rules().find({"org_id": org_id}).sort("created_at", -1)
    return await cursor.to_list(length=200)


async def find_enabled_rules(org_id: str) -> list[dict]:
    cursor = alert_rules().find({"org_id": org_id, "enabled": True})
    return await cursor.to_list(length=200)


async def set_rule_enabled(org_id: str, rule_id: str, enabled: bool) -> None:
    await alert_rules().update_one({"org_id": org_id, "_id": ObjectId(rule_id)}, {"$set": {"enabled": enabled}})


async def delete_rule(org_id: str, rule_id: str) -> None:
    await alert_rules().delete_one({"org_id": org_id, "_id": ObjectId(rule_id)})


async def insert_notification(org_id: str, doc: dict) -> dict:
    doc = dict(doc)
    doc["org_id"] = org_id
    doc.setdefault("read", False)
    doc.setdefault("created_at", datetime.now(timezone.utc))
    res = await notifications().insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def recent_notification_exists(org_id: str, rule_id: str, since: datetime) -> bool:
    doc = await notifications().find_one({"org_id": org_id, "rule_id": rule_id, "created_at": {"$gte": since}})
    return doc is not None


async def list_notifications(org_id: str, limit: int = 50) -> list[dict]:
    cursor = notifications().find({"org_id": org_id}).sort("created_at", -1)
    return await cursor.to_list(length=limit)


async def mark_read(org_id: str, notification_id: str) -> None:
    await notifications().update_one(
        {"org_id": org_id, "_id": ObjectId(notification_id)}, {"$set": {"read": True}}
    )


async def mark_all_read(org_id: str) -> None:
    await notifications().update_many({"org_id": org_id, "read": False}, {"$set": {"read": True}})
