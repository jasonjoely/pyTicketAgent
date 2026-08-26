"""Protocol for incident ticket persistence."""

from __future__ import annotations

from typing import Protocol

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket


class TicketRepository(Protocol):
    """Data access for incident tickets, including embeddings and search."""

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        """Return the ticket with the given id, or None if not found."""
        ...

    async def get_embedding_meta(
        self, ticket_id: int
    ) -> TicketEmbeddingMeta | None:
        """Return embedding metadata for hash-skip decisions, or None if missing."""
        ...

    async def search_fts(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        """Full-text search ranked by relevance, with optional filters/limit."""
        ...

    async def search_semantic(
        self,
        query_vector: list[float],
        space: EmbeddingSpace,
        filter_: TicketFilter | None = None,
        limit: int | None = None,
    ) -> list[IncidentTicket]:
        """Nearest-neighbor search against one embedding space."""
        ...

    async def upsert(
        self,
        ticket: IncidentTicket,
        embeddings: TicketEmbeddingsWrite | None = None,
    ) -> UpsertOutcome:
        """Insert or update a ticket by id. Returns Created or Updated."""
        ...
