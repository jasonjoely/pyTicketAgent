"""Tests for dual-space embedding behavior during ingest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.embedding_space_write import EmbeddingSpaceWrite
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embedding_space_meta import (
    TicketEmbeddingSpaceMeta,
)
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_core.tickets.ticket_state import TicketState

from pyticketagent_api.models.incident_ticket_request import IncidentTicketRequest
from pyticketagent_api.services.ticket_ingest_service import TicketIngestService


class _FakeEmbeddingClient:
    def __init__(
        self,
        vector: list[float] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.vector = vector
        self.error = error
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if self.error is not None:
            raise self.error
        assert self.vector is not None
        return [list(self.vector) for _ in texts]


class _FakeTicketRepository:
    def __init__(
        self,
        existing_meta: TicketEmbeddingMeta | None = None,
    ) -> None:
        self.existing_meta = existing_meta
        self.upserts: list[tuple[IncidentTicket, TicketEmbeddingsWrite | None]] = []

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        raise NotImplementedError

    async def get_embedding_meta(self, ticket_id: int) -> TicketEmbeddingMeta | None:
        return self.existing_meta

    async def search_fts(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        raise NotImplementedError

    async def search_semantic(
        self,
        query_vector: list[float],
        space: EmbeddingSpace,
        filter_: TicketFilter | None = None,
        limit: int | None = None,
    ) -> list[IncidentTicket]:
        raise NotImplementedError

    async def upsert(
        self,
        ticket: IncidentTicket,
        embeddings: TicketEmbeddingsWrite | None = None,
    ) -> UpsertOutcome:
        self.upserts.append((ticket, embeddings))
        return UpsertOutcome.CREATED


def _request(**overrides: Any) -> IncidentTicketRequest:
    data: dict[str, Any] = {
        "id": 42,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "environment": "production",
        "service": "api",
        "title": "Error",
        "description": "Something failed",
        "resolution_summary": "",
        "tags": ["bug"],
        "severity": 1,
    }
    data.update(overrides)
    return IncidentTicketRequest.model_validate(data)


def _binding(provider: str, model: str) -> EmbeddingModelBinding:
    return EmbeddingModelBinding(provider_id=provider, model=model, dimensions=3)


def _runtime(
    fastembed: _FakeEmbeddingClient,
    ollama: _FakeEmbeddingClient,
    *,
    fastembed_enabled: bool = True,
    ollama_enabled: bool = True,
) -> DualSpaceEmbeddingRuntime:
    from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace

    return DualSpaceEmbeddingRuntime(
        fastembed_client=fastembed,
        fastembed_binding=_binding("fastembed", "BAAI/bge-base-en-v1.5"),
        fastembed_enabled=fastembed_enabled,
        ollama_client=ollama,
        ollama_binding=_binding("ollama", "nomic-embed-text"),
        ollama_enabled=ollama_enabled,
        default_search_space=EmbeddingSpace.FASTEMBED,
    )


@pytest.mark.asyncio
async def test_ingest_soft_fails_one_space_to_null() -> None:
    fastembed = _FakeEmbeddingClient(vector=[0.1, 0.2, 0.3])
    ollama = _FakeEmbeddingClient(error=RuntimeError("ollama down"))
    repo = _FakeTicketRepository()
    service = TicketIngestService(
        repo,
        embedding_runtime=_runtime(fastembed, ollama),
    )

    response = await service.ingest([_request()])

    assert response.counts.ingested == 1
    assert len(repo.upserts) == 1
    _, write = repo.upserts[0]
    assert write is not None
    assert write.fastembed.update is True
    assert write.fastembed.vector == [0.1, 0.2, 0.3]
    assert write.ollama == EmbeddingSpaceWrite.clear()
    assert fastembed.calls
    assert ollama.calls


@pytest.mark.asyncio
async def test_ingest_skips_unchanged_hash_and_model() -> None:
    from pyticketagent_core.embeddings.embedding_content_hasher import (
        EmbeddingContentHasher,
    )
    from pyticketagent_core.embeddings.ticket_embedding_text_builder import (
        TicketEmbeddingTextBuilder,
    )
    from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace

    builder = TicketEmbeddingTextBuilder()
    hasher = EmbeddingContentHasher()
    ticket = IncidentTicket(
        id=42,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        environment="production",
        service="api",
        title="Error",
        description="Something failed",
        resolution_summary="",
        tags=["bug"],
        severity=1,
        status=TicketState.UNASSIGNED,
    )
    fe_hash = hasher.hash_text(
        builder.build_document(ticket, EmbeddingSpace.FASTEMBED)
    )
    ol_hash = hasher.hash_text(builder.build_document(ticket, EmbeddingSpace.OLLAMA))

    fastembed = _FakeEmbeddingClient(vector=[0.1, 0.2, 0.3])
    ollama = _FakeEmbeddingClient(vector=[0.4, 0.5, 0.6])
    repo = _FakeTicketRepository(
        existing_meta=TicketEmbeddingMeta(
            fastembed=TicketEmbeddingSpaceMeta(
                model="fastembed:BAAI/bge-base-en-v1.5",
                content_hash=fe_hash,
                has_vector=True,
            ),
            ollama=TicketEmbeddingSpaceMeta(
                model="ollama:nomic-embed-text",
                content_hash=ol_hash,
                has_vector=True,
            ),
        )
    )
    service = TicketIngestService(
        repo,
        embedding_runtime=_runtime(fastembed, ollama),
    )

    await service.ingest([_request()])

    _, write = repo.upserts[0]
    assert write is not None
    assert write.fastembed == EmbeddingSpaceWrite.preserve()
    assert write.ollama == EmbeddingSpaceWrite.preserve()
    assert fastembed.calls == []
    assert ollama.calls == []


@pytest.mark.asyncio
async def test_ingest_clears_both_spaces_when_both_fail() -> None:
    fastembed = _FakeEmbeddingClient(error=RuntimeError("fastembed fail"))
    ollama = _FakeEmbeddingClient(error=RuntimeError("ollama fail"))
    repo = _FakeTicketRepository()
    service = TicketIngestService(
        repo,
        embedding_runtime=_runtime(fastembed, ollama),
    )

    response = await service.ingest([_request()])

    assert response.counts.ingested == 1
    _, write = repo.upserts[0]
    assert write is not None
    assert write.fastembed == EmbeddingSpaceWrite.clear()
    assert write.ollama == EmbeddingSpaceWrite.clear()
