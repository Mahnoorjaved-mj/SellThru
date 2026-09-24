"""Product master data access."""
from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId
from pymongo import UpdateOne

from app.repositories.base import products


async def upsert(org_id: str, product_id: str, fields: dict) -> None:
    now = datetime.now(timezone.utc)
    await products().update_one(
        {"org_id": org_id, "product_id": product_id},
        {"$set": {**fields, "updated_at": now}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def bulk_upsert(org_id: str, items: list[dict], chunk_size: int = 1000) -> int:
    """Fast bulk upsert of product master records during CSV import."""
    if not items:
        return 0
    now = datetime.now(timezone.utc)
    ops = [
        UpdateOne(
            {"org_id": org_id, "product_id": item["product_id"]},
            {
                "$set": {
                    "category": item.get("category", "Uncategorized"),
                    "is_active": True,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                    "unit_price": item.get("unit_price"),
                },
            },
            upsert=True,
        )
        for item in items
    ]
    total = 0
    for i in range(0, len(ops), chunk_size):
        chunk = ops[i:i + chunk_size]
        res = await products().bulk_write(chunk, ordered=False)
        total += (res.upserted_count + res.modified_count)
    return total


async def count(org_id: str, search: str | None = None) -> int:
    q = {"org_id": org_id}
    if search:
        q["$or"] = [
            {"product_id": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
        ]
    return await products().count_documents(q)


async def find_paginated(org_id: str, skip: int = 0, limit: int = 50, search: str | None = None) -> list[dict]:
    q = {"org_id": org_id}
    if search:
        q["$or"] = [
            {"product_id": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}},
        ]
    cursor = products().find(q).sort("product_id", 1).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


async def list_all(org_id: str, limit: int = 10000) -> list[dict]:
    cursor = products().find({"org_id": org_id}).sort("product_id", 1)
    return await cursor.to_list(length=limit)


async def find_by_id(org_id: str, oid: str) -> dict | None:
    return await products().find_one({"org_id": org_id, "_id": ObjectId(oid)})


async def update_fields(org_id: str, oid: str, fields: dict) -> None:
    await products().update_one(
        {"org_id": org_id, "_id": ObjectId(oid)},
        {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}},
    )


async def delete(org_id: str, oid: str) -> None:
    await products().delete_one({"org_id": org_id, "_id": ObjectId(oid)})
