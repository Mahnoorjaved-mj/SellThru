"""Smoke tests for the liveness/readiness endpoints."""
from __future__ import annotations


async def test_healthz_is_always_ok(client):
    res = await client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_readyz_reports_db_connectivity(client):
    res = await client.get("/readyz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("healthy", "degraded")
    assert "db" in body and "ok" in body["db"]


async def test_legacy_health_alias_still_works(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert "db" in res.json()


async def test_request_id_header_present(client):
    res = await client.get("/healthz")
    assert "x-request-id" in {k.lower() for k in res.headers.keys()}
