"""Proves that sales_repo never leaks documents across organizations.

This is the repository-level version of the DoD requirement "a test proves
cross-org access returns 404/403". There is no endpoint-level cross-org
surface yet (a user belongs to exactly one org and there is no org-switching
API) — that becomes testable end-to-end once Phase 7 adds organization
membership and admin cross-org browsing. Until then, this is the load-bearing
guarantee: every query is physically filtered by org_id at the data layer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from app.repositories import sales_repo


async def _seed(org_id: str, store_id: str, n: int = 3) -> None:
    docs = [
        {
            "date": datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            "store_id": store_id,
            "product_id": "PROD-TEST",
            "category": "Test",
            "quantity": 10 + i,
            "revenue": 100.0 + i,
            "is_holiday": False,
            "is_promo": False,
        }
        for i in range(n)
    ]
    await sales_repo.insert_many(org_id, docs)


async def test_sales_count_is_isolated_per_org():
    org_a = str(ObjectId())
    org_b = str(ObjectId())

    await _seed(org_a, "Store-A", n=3)
    await _seed(org_b, "Store-B", n=5)

    assert await sales_repo.count(org_a) == 3
    assert await sales_repo.count(org_b) == 5


async def test_sales_find_paginated_never_crosses_org():
    org_a = str(ObjectId())
    org_b = str(ObjectId())

    await _seed(org_a, "Store-A", n=2)
    await _seed(org_b, "Store-B", n=2)

    docs_a = await sales_repo.find_paginated(org_a, {}, skip=0, limit=50)
    assert len(docs_a) == 2
    assert all(d["store_id"] == "Store-A" for d in docs_a)
    assert all(d["org_id"] == org_a for d in docs_a)


async def test_sales_aggregate_prepends_org_match():
    org_a = str(ObjectId())
    org_b = str(ObjectId())

    await _seed(org_a, "Store-A", n=2)
    await _seed(org_b, "Store-B", n=4)

    pipeline = [{"$group": {"_id": None, "total": {"$sum": 1}}}]
    res_a = await sales_repo.aggregate(org_a, pipeline)
    res_b = await sales_repo.aggregate(org_b, pipeline)

    assert res_a[0]["total"] == 2
    assert res_b[0]["total"] == 4


async def test_sales_repo_requires_org_id_argument():
    """Calling without org_id is a TypeError, not a silent unscoped query."""
    import inspect

    sig = inspect.signature(sales_repo.count)
    assert list(sig.parameters)[0] == "org_id"
    assert sig.parameters["org_id"].default is inspect.Parameter.empty
