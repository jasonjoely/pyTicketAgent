"""Stored metadata for one embedding space on a ticket."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TicketEmbeddingSpaceMeta:
    """Model / content hash / presence for one space."""

    model: str | None
    content_hash: str | None
    has_vector: bool
