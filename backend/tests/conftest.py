"""Shared test fixtures.

Runs against a dedicated `<MONGO_DB_NAME>_test` database on the same Atlas
cluster configured in .env (there's no local Mongo in this environment).
The test database is dropped once at the end of the whole session.
"""
from __future__ import annotations

import os

# Must happen before any `app.*` import: Settings() is a cached singleton
# read at import time, so the env var has to be set first.
_base_db_name = os.environ.get("MONGO_DB_NAME", "Sellthru")
if not _base_db_name.endswith("_test"):
    os.environ["MONGO_DB_NAME"] = f"{_base_db_name}_test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.db import close, connect
from app.core.db import get_db as _get_db


@pytest_asyncio.fixture(autouse=True)
async def db_lifecycle():
    """Connect (idempotent) at the start of each test, close after.

    Function-scoped on purpose: Motor's client is bound to the event loop it
    was created on, and pytest-asyncio gives each test its own loop by
    default. Reconnecting per test keeps the client and the loop in sync.
    """
    connect()
    yield
    close()


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def pytest_sessionfinish(session, exitstatus):
    """Drop the test database once, via a plain sync client (no event-loop coupling)."""
    from pymongo import MongoClient

    sync_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        sync_client.drop_database(settings.MONGO_DB_NAME)
    except Exception:
        pass
    finally:
        sync_client.close()
