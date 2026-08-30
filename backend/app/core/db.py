"""MongoDB (Motor) async client lifecycle."""
from __future__ import annotations

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

log = logging.getLogger("forecastiq.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def connect() -> AsyncIOMotorDatabase:
    """Create the Motor client (idempotent) and return the database handle."""
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
        _db = _client[settings.MONGO_DB_NAME]
        log.info("Connected to MongoDB db=%s", settings.MONGO_DB_NAME)
    return _db


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        return connect()
    return _db


def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
