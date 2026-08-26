"""Per-request correlation ID, propagated to log records via a contextvar."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator
from uuid import uuid4

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the request ID for the current context, or ``"-"`` outside a request."""
    return _request_id.get()


@contextmanager
def request_scope(request_id: str | None = None) -> Iterator[str]:
    """Bind a request ID (generating one if omitted) for the duration of the block."""
    token = _request_id.set(request_id or uuid4().hex)
    try:
        yield _request_id.get()
    finally:
        _request_id.reset(token)
