"""Full-text / hybrid search query with optional filters."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace


@dataclass(frozen=True, slots=True)
class TicketSearchQuery:
    """Search text plus optional structured filters and limits."""

    search_text: str
    filter: TicketFilter | None = None
    embedding_space: EmbeddingSpace | None = None
    limit: int | None = None
