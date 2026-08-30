"""Raw Mongo collection accessors + index/organization bootstrap.

This is the only module allowed to know Motor collection names. Everything
else goes through the per-entity repository modules in this package.
"""
from __future__ import annotations

import structlog
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING

from app.core.db import get_db

log = structlog.get_logger("forecastiq.db")

DEFAULT_ORG_SLUG = "default"
DEFAULT_ORG_NAME = "Default Organization"


def users():
    return get_db()["users"]


def otp():
    return get_db()["otp_verification"]


def reset_tokens():
    return get_db()["password_reset_tokens"]


def sales():
    return get_db()["sales"]


def forecasts():
    return get_db()["forecasts"]


def models():
    return get_db()["models"]


def audit_events():
    return get_db()["audit_events"]


def twofa():
    return get_db()["user_2fa_secrets"]


def organizations():
    return get_db()["organizations"]


def products():
    return get_db()["products"]


def stores():
    return get_db()["stores"]


def imports():
    return get_db()["imports"]


def anomaly_acknowledgements():
    return get_db()["anomaly_acknowledgements"]


def alert_rules():
    return get_db()["alert_rules"]


def notifications():
    return get_db()["notifications"]


def sessions():
    return get_db()["sessions"]


async def ensure_default_org() -> str:
    """Create (if missing) the Default Organization and return its id as a string.

    Every collection is schema-ready for multi-tenancy (org_id field + indexes),
    but organization management (creation, invites, membership) is not built yet —
    everything belongs to this single org until that lands.
    """
    existing = await organizations().find_one({"slug": DEFAULT_ORG_SLUG})
    if existing:
        return str(existing["_id"])

    now = datetime.now(timezone.utc)
    res = await organizations().insert_one(
        {
            "name": DEFAULT_ORG_NAME,
            "slug": DEFAULT_ORG_SLUG,
            "is_default": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    log.info("created_default_organization", org_id=str(res.inserted_id))
    return str(res.inserted_id)


async def backfill_org_ids(default_org_id: str) -> None:
    """Assign every pre-existing document without org_id to the default org."""
    for coll, label in (
        (users(), "users"),
        (sales(), "sales"),
        (forecasts(), "forecasts"),
        (models(), "models"),
    ):
        res = await coll.update_many({"org_id": {"$exists": False}}, {"$set": {"org_id": default_org_id}})
        if res.modified_count:
            log.info("backfilled_org_id", collection=label, count=res.modified_count)


async def ensure_indexes() -> None:
    """Create database indexes."""
    await users().create_index([("email", ASCENDING)], unique=True)
    await users().create_index([("org_id", ASCENDING)])
    await otp().create_index([("email", ASCENDING)])
    await otp().create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await reset_tokens().create_index([("token", ASCENDING)], unique=True)
    await reset_tokens().create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

    # Org-scoped compound indexes for fast, isolated querying
    await sales().create_index([("org_id", ASCENDING), ("date", ASCENDING)])
    await sales().create_index(
        [("org_id", ASCENDING), ("store_id", ASCENDING), ("product_id", ASCENDING), ("date", ASCENDING)]
    )
    await sales().create_index([("org_id", ASCENDING), ("category", ASCENDING)])
    await sales().create_index([("org_id", ASCENDING), ("import_id", ASCENDING)])
    await sales().create_index(
        [("org_id", ASCENDING), ("row_hash", ASCENDING)],
        unique=True,
        partialFilterExpression={"row_hash": {"$exists": True}},
    )

    await products().create_index([("org_id", ASCENDING), ("product_id", ASCENDING)], unique=True)
    await stores().create_index([("org_id", ASCENDING), ("store_id", ASCENDING)], unique=True)
    await imports().create_index([("org_id", ASCENDING), ("created_at", DESCENDING)])
    await imports().create_index([("org_id", ASCENDING), ("file_hash", ASCENDING)])

    await forecasts().create_index(
        [("org_id", ASCENDING), ("store_id", ASCENDING), ("product_id", ASCENDING), ("target_date", ASCENDING)]
    )
    await models().create_index([("org_id", ASCENDING), ("trained_at", DESCENDING)])

    await audit_events().create_index([("user_id", ASCENDING), ("occurred_at", DESCENDING)])
    await audit_events().create_index([("org_id", ASCENDING), ("occurred_at", DESCENDING)])
    await twofa().create_index([("user_id", ASCENDING)], unique=True)
    await organizations().create_index([("slug", ASCENDING)], unique=True)

    await sessions().create_index([("token_hash", ASCENDING)], unique=True)
    await sessions().create_index([("user_id", ASCENDING)])
    await sessions().create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    await alert_rules().create_index([("org_id", ASCENDING)])
    await notifications().create_index([("org_id", ASCENDING), ("created_at", DESCENDING)])
    await anomaly_acknowledgements().create_index([("org_id", ASCENDING), ("key", ASCENDING)], unique=True)
    log.info("indexes_ensured")
