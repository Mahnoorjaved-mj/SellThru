"""Shared model helpers — Mongo document serialization."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from bson import ObjectId


def oid_str(value: Any) -> str | None:
    """Return a string form of an ObjectId (or None)."""
    if value is None:
        return None
    return str(value)


def serialize(doc: dict | None) -> dict | None:
    """Convert a Mongo document into a JSON-friendly dict.

    `_id` becomes `id` (string); nested ObjectId/datetime values are coerced.
    """
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for k, v in doc.items():
        key = "id" if k == "_id" else k
        out[key] = _coerce(v)
    return out


def _coerce(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [_coerce(x) for x in v]
    if isinstance(v, dict):
        return {k: _coerce(x) for k, x in v.items()}
    return v
