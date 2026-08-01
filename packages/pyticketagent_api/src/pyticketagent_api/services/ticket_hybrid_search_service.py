"""Hybrid FTS + semantic search fused with Reciprocal Rank Fusion."""

from __future__ import annotations

import asyncio
import logging

from pyticketagent_core.data.rrf_rank_fusion import RrfRankFusion
from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_text_builder import (
    TicketEmbeddingTextBuilder,
)
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

logger = logging.getLogger(__name__)

_PER_LEG_LIMIT = 20
_DEFAULT_RESULT_LIMIT = 10


class TicketHybridSearchService:
    """Run FTS + one embedding space, fuse with RRF, soft-fail to FTS-only."""

    def __init__(
        self,
        ticket_repository: TicketRepository,
        embedding_runtime: DualSpaceEmbeddingRuntime | None,
        text_builder: TicketEmbeddingTextBuilder | None = None,
        rank_fusion: RrfRankFusion | None = None,
        per_leg_limit: int = _PER_LEG_LIMIT,
        result_limit: int = _DEFAULT_RESULT_LIMIT,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._embedding_runtime = embedding_runtime
        self._text_builder = text_builder or TicketEmbeddingTextBuilder()
        self._rank_fusion = rank_fusion or RrfRankFusion()
        self._per_leg_limit = per_leg_limit
        self._result_limit = result_limit

    async def search(
        self,
        search_text: str,
        filter_: TicketFilter | None = None,
        embedding_space: EmbeddingSpace | None = None,
        limit: int | None = None,
    ) -> list[IncidentTicket]:
        """Return hybrid-ranked tickets (FTS + semantic), truncated to ``limit``."""
        text = search_text.strip()
        if not text:
            return []

        result_limit = limit if limit is not None else self._result_limit
        ticket_filter = filter_ or TicketFilter()

        fts_task = self._ticket_repository.search_fts(
            TicketSearchQuery(
                search_text=text,
                filter=ticket_filter,
                limit=self._per_leg_limit,
            )
        )
        semantic_task = self._search_semantic_leg(
            text, ticket_filter, embedding_space
        )
        fts_tickets, semantic_tickets = await asyncio.gather(
            fts_task, semantic_task
        )

        if not semantic_tickets:
            return fts_tickets[:result_limit]

        fused_ids = self._rank_fusion.fuse(
            [ticket.id for ticket in fts_tickets],
            [ticket.id for ticket in semantic_tickets],
        )
        by_id = {
            ticket.id: ticket for ticket in (*fts_tickets, *semantic_tickets)
        }
        return [
            by_id[ticket_id]
            for ticket_id in fused_ids[:result_limit]
            if ticket_id in by_id
        ]

    async def _search_semantic_leg(
        self,
        search_text: str,
        filter_: TicketFilter,
        embedding_space: EmbeddingSpace | None,
    ) -> list[IncidentTicket]:
        runtime = self._embedding_runtime
        if runtime is None:
            logger.warning(
                "Embedding runtime unavailable; hybrid search using FTS-only."
            )
            return []

        space = embedding_space or runtime.default_search_space
        client, enabled = self._resolve_space_client(runtime, space)
        if not enabled or client is None:
            logger.warning(
                "Embedding space '%s' is disabled or unavailable; "
                "hybrid search using FTS-only.",
                space.value,
            )
            return []

        try:
            query_text = self._text_builder.build_query(search_text, space)
            vectors = await client.embed([query_text])
            if not vectors:
                logger.warning(
                    "Embedding space '%s' returned no query vector; "
                    "hybrid search using FTS-only.",
                    space.value,
                )
                return []
            return await self._ticket_repository.search_semantic(
                vectors[0],
                space,
                filter_=filter_,
                limit=self._per_leg_limit,
            )
        except Exception:
            logger.exception(
                "Semantic search failed for space '%s'; hybrid search using FTS-only.",
                space.value,
            )
            return []

    @staticmethod
    def _resolve_space_client(
        runtime: DualSpaceEmbeddingRuntime,
        space: EmbeddingSpace,
    ):
        if space == EmbeddingSpace.FASTEMBED:
            return runtime.fastembed_client, runtime.fastembed_enabled
        return runtime.ollama_client, runtime.ollama_enabled
