"""Format Python float lists as pgvector text literals."""

from __future__ import annotations


def format_pgvector_literal(values: list[float] | None) -> str | None:
    """Return ``[f1,f2,...]`` for asyncpg ``::vector`` binds, or None."""
    if values is None:
        return None
    return "[" + ",".join(str(float(v)) for v in values) + "]"
