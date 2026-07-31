"""Stored embedding metadata for both POC spaces."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.embeddings.ticket_embedding_space_meta import (
    TicketEmbeddingSpaceMeta,
)


@dataclass(frozen=True, slots=True)
class TicketEmbeddingMeta:
    """Per-space embedding metadata used for hash skip decisions."""

    fastembed: TicketEmbeddingSpaceMeta
    ollama: TicketEmbeddingSpaceMeta
