"""Per-request context (request id) shared between middleware, logging, and error handlers."""
from __future__ import annotations

from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    _request_id_var.set(value)
