"""Tracks anomalies a user has acknowledged / marked as expected, so they
stop surfacing in future anomaly scans for that exact store/product/date.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.base import anomaly_acknowledgements as _coll


def _key(store_id: str, product_id: str, date_iso: str) -> str:
    return f"{store_id}|{product_id}|{date_iso}"


async def acknowledge(org_id: str, store_id: str, product_id: str, date_iso: str, user_id: str) -> None:
    await _coll().update_one(
        {"org_id": org_id, "key": _key(store_id, product_id, date_iso)},
        {"$set": {
            "org_id": org_id, "store_id": store_id, "product_id": product_id, "date": date_iso,
            "acknowledged_by": user_id, "acknowledged_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def list_acknowledged_keys(org_id: str) -> set[str]:
    cursor = _coll().find({"org_id": org_id}, {"key": 1})
    docs = await cursor.to_list(length=5000)
    return {d["key"] for d in docs}
