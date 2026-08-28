"""Tests for ticket embedding text composition."""

from datetime import datetime, timezone

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_text_builder import (
    TicketEmbeddingTextBuilder,
)
from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_core.tickets.ticket_state import TicketState


def _ticket(**overrides: object) -> IncidentTicket:
    data: dict[str, object] = {
        "id": 1,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "environment": "production",
        "service": "redis",
        "title": "Timeouts",
        "description": "Clients see timeouts",
        "resolution_summary": "Increased pool size",
        "tags": ["cache", "latency"],
        "severity": 2,
        "status": TicketState.RESOLVED,
    }
    data.update(overrides)
    return IncidentTicket.model_validate(data)


def test_build_document_includes_metadata_and_resolution() -> None:
    text = TicketEmbeddingTextBuilder().build_document(
        _ticket(), EmbeddingSpace.FASTEMBED
    )
    assert "Service: redis" in text
    assert "Environment: production" in text
    assert "Tags: cache, latency" in text
    assert "Title: Timeouts" in text
    assert "Clients see timeouts" in text
    assert "Resolution: Increased pool size" in text
    assert not text.startswith("search_document:")


def test_build_document_omits_empty_resolution() -> None:
    text = TicketEmbeddingTextBuilder().build_document(
        _ticket(resolution_summary=""), EmbeddingSpace.FASTEMBED
    )
    assert "Resolution:" not in text


def test_ollama_document_uses_nomic_prefix() -> None:
    text = TicketEmbeddingTextBuilder().build_document(
        _ticket(), EmbeddingSpace.OLLAMA
    )
    assert text.startswith("search_document: ")
    assert "Service: redis" in text


def test_ollama_query_uses_nomic_prefix() -> None:
    text = TicketEmbeddingTextBuilder().build_query(
        " redis timeouts ", EmbeddingSpace.OLLAMA
    )
    assert text == "search_query: redis timeouts"
