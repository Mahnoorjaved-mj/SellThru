"""Persisted forecast run access.

Not yet written to by any service (Phase 5 introduces saved forecast runs);
this module + the collection's org-scoped indexes exist now so that work
doesn't need a schema migration later.
"""
from __future__ import annotations

from app.repositories.base import forecasts


async def insert_many(org_id: str, records: list[dict]) -> int:
    for r in records:
        r["org_id"] = org_id
    if not records:
        return 0
    res = await forecasts().insert_many(records)
    return len(res.inserted_ids)


async def find_for_target(org_id: str, store_id: str, product_id: str, limit: int = 200) -> list[dict]:
    cursor = (
        forecasts()
        .find({"org_id": org_id, "store_id": store_id, "product_id": product_id})
        .sort("target_date", 1)
    )
    return await cursor.to_list(length=limit)
