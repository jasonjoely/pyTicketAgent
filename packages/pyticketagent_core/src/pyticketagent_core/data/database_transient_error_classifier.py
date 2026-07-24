"""Classify whether a database exception is transient and worth retrying."""

import asyncpg

# Postgres SQLSTATE codes that indicate transient failures (ported from DFAgent).
_TRANSIENT_SQLSTATES = frozenset(
    {
        "40001",  # serialization_failure
        "40P01",  # deadlock_detected
        "53300",  # too_many_connections
        "57P01",  # admin_shutdown
        "57P03",  # cannot_connect_now
    }
)

_CLIENT_TRANSIENT_TYPES: tuple[type[BaseException], ...] = (
    asyncpg.InterfaceError,
    ConnectionError,
    TimeoutError,
    OSError,
)
_InternalClientError = getattr(asyncpg, "InternalClientError", None)
if isinstance(_InternalClientError, type):
    _CLIENT_TRANSIENT_TYPES = (*_CLIENT_TRANSIENT_TYPES, _InternalClientError)


def is_transient_exception(exc: BaseException) -> bool:
    """Return True if ``exc`` (or a nested cause) is a transient DB error."""
    if isinstance(exc, asyncpg.PostgresError) and getattr(exc, "sqlstate", None) in _TRANSIENT_SQLSTATES:
        return True

    if isinstance(exc, _CLIENT_TRANSIENT_TYPES):
        return True

    cause = exc.__cause__
    if cause is not None and cause is not exc:
        return is_transient_exception(cause)

    context = exc.__context__
    if context is not None and context is not exc:
        return is_transient_exception(context)

    return False
