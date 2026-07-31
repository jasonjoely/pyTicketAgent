"""Per-space write instruction for ticket upsert."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EmbeddingSpaceWrite:
    """How to update one embedding column group on upsert.

    When ``update`` is False, existing DB values for that space are preserved.
    When ``update`` is True and ``vector`` is None, the space is cleared to NULL.
    """

    update: bool
    vector: list[float] | None = None
    model: str | None = None
    content_hash: str | None = None
    updated_at: datetime | None = None

    @staticmethod
    def preserve() -> EmbeddingSpaceWrite:
        return EmbeddingSpaceWrite(update=False)

    @staticmethod
    def clear() -> EmbeddingSpaceWrite:
        return EmbeddingSpaceWrite(update=True)

    @staticmethod
    def set_vector(
        vector: list[float],
        *,
        model: str,
        content_hash: str,
        updated_at: datetime,
    ) -> EmbeddingSpaceWrite:
        return EmbeddingSpaceWrite(
            update=True,
            vector=vector,
            model=model,
            content_hash=content_hash,
            updated_at=updated_at,
        )
