"""Tests for hybrid FTS + semantic search service."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_core.tickets.ticket_state import TicketState
from pyticketagent_api.services.ticket_hybrid_search_service import (
    TicketHybridSearchService,
)


def _ticket(ticket_id: int, title: str = "t") -> IncidentTicket:
    return IncidentTicket(
        id=ticket_id,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        environment="production",
        service="api",
        title=title,
        description="desc",
        resolution_summary="fixed",
        tags=["x"],
        severity=2,
        status=TicketState.RESOLVED,
    )


class _FakeEmbeddingClient:
    def __init__(
        self,
        vector: list[float] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.vector = vector
        self.error = error
        self.texts: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts.extend(texts)
        if self.error is not None:
            raise self.error
        assert self.vector is not None
        return [list(self.vector) for _ in texts]


class _FakeTicketRepository:
    def __init__(
        self,
        fts: list[IncidentTicket] | None = None,
        semantic: list[IncidentTicket] | None = None,
    ) -> None:
        self.fts = fts or []
        self.semantic = semantic or []
        self.fts_queries: list[TicketSearchQuery] = []
        self.semantic_calls: list[tuple[list[float], EmbeddingSpace, int | None]] = []

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        raise NotImplementedError

    async def get_embedding_meta(self, ticket_id: int) -> TicketEmbeddingMeta | None:
        raise NotImplementedError

    async def upsert(
        self,
        ticket: IncidentTicket,
        embeddings: TicketEmbeddingsWrite | None = None,
    ) -> UpsertOutcome:
        raise NotImplementedError

    async def search_fts(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        self.fts_queries.append(query)
        return list(self.fts)

    async def search_semantic(
        self,
        query_vector: list[float],
        space: EmbeddingSpace,
        filter_: TicketFilter | None = None,
        limit: int | None = None,
    ) -> list[IncidentTicket]:
        self.semantic_calls.append((query_vector, space, limit))
        return list(self.semantic)


def _binding(provider: str, model: str) -> EmbeddingModelBinding:
    return EmbeddingModelBinding(provider_id=provider, model=model, dimensions=3)


def _runtime(
    fastembed: _FakeEmbeddingClient,
    ollama: _FakeEmbeddingClient,
    *,
    fastembed_enabled: bool = True,
    ollama_enabled: bool = True,
    default_search_space: EmbeddingSpace = EmbeddingSpace.OLLAMA,
) -> DualSpaceEmbeddingRuntime:
    return DualSpaceEmbeddingRuntime(
        fastembed_client=fastembed,
        fastembed_binding=_binding("fastembed", "m"),
        fastembed_enabled=fastembed_enabled,
        ollama_client=ollama,
        ollama_binding=_binding("ollama", "n"),
        ollama_enabled=ollama_enabled,
        default_search_space=default_search_space,
    )


@pytest.mark.asyncio
async def test_hybrid_fuses_fts_and_semantic() -> None:
    repo = _FakeTicketRepository(
        fts=[_ticket(1), _ticket(2), _ticket(3)],
        semantic=[_ticket(2), _ticket(4)],
    )
    fastembed = _FakeEmbeddingClient(vector=[0.1, 0.2, 0.3])
    ollama = _FakeEmbeddingClient(vector=[0.4, 0.5, 0.6])
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=_runtime(fastembed, ollama),
        result_limit=10,
    )

    results = await service.search("timeout")
    assert [t.id for t in results][0] == 2
    assert {t.id for t in results} == {1, 2, 3, 4}
    assert ollama.texts  # default space
    assert not fastembed.texts
    assert repo.semantic_calls[0][1] == EmbeddingSpace.OLLAMA


@pytest.mark.asyncio
async def test_embedding_space_override_uses_fastembed() -> None:
    repo = _FakeTicketRepository(fts=[_ticket(1)], semantic=[_ticket(1)])
    fastembed = _FakeEmbeddingClient(vector=[0.1, 0.2, 0.3])
    ollama = _FakeEmbeddingClient(vector=[0.4, 0.5, 0.6])
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=_runtime(fastembed, ollama),
    )

    await service.search("q", embedding_space=EmbeddingSpace.FASTEMBED)
    assert fastembed.texts
    assert not ollama.texts
    assert repo.semantic_calls[0][1] == EmbeddingSpace.FASTEMBED


@pytest.mark.asyncio
async def test_embed_failure_falls_back_to_fts_only() -> None:
    repo = _FakeTicketRepository(
        fts=[_ticket(1), _ticket(2)],
        semantic=[_ticket(99)],
    )
    ollama = _FakeEmbeddingClient(error=RuntimeError("ollama down"))
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=_runtime(_FakeEmbeddingClient(vector=[1.0]), ollama),
    )

    results = await service.search("timeout")
    assert [t.id for t in results] == [1, 2]
    assert repo.semantic_calls == []


@pytest.mark.asyncio
async def test_disabled_space_falls_back_to_fts_only() -> None:
    repo = _FakeTicketRepository(fts=[_ticket(5)], semantic=[_ticket(9)])
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=_runtime(
            _FakeEmbeddingClient(vector=[1.0]),
            _FakeEmbeddingClient(vector=[2.0]),
            ollama_enabled=False,
        ),
    )

    results = await service.search("timeout")
    assert [t.id for t in results] == [5]
    assert repo.semantic_calls == []


@pytest.mark.asyncio
async def test_missing_runtime_falls_back_to_fts_only() -> None:
    repo = _FakeTicketRepository(fts=[_ticket(7)])
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=None,
    )

    results = await service.search("timeout")
    assert [t.id for t in results] == [7]


@pytest.mark.asyncio
async def test_result_limit_truncates() -> None:
    repo = _FakeTicketRepository(
        fts=[_ticket(i) for i in range(1, 6)],
        semantic=[],
    )
    service = TicketHybridSearchService(
        ticket_repository=repo,
        embedding_runtime=None,
        result_limit=10,
    )

    results = await service.search("q", limit=2)
    assert [t.id for t in results] == [1, 2]
