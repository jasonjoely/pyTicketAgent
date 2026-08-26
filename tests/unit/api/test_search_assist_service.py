"""Tests for SearchAssistService."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind
from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.assist.search_assist_prompt_builder import (
    SearchAssistPromptBuilder,
)
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.models.assist_request import AssistRequest
from pyticketagent_api.services.search_assist_service import SearchAssistService
from pyticketagent_api.services.ticket_assist_parse_exception import (
    TicketAssistParseException,
)
from pyticketagent_api.services.ticket_hybrid_search_service import (
    TicketHybridSearchService,
)

_PROVIDER = AiProviderDefinition(id="fake-provider", kind=AiProviderKind.OLLAMA)
_BINDING = AiModelBinding(provider_id="fake-provider", model="fake-model")


def _ticket(ticket_id: int) -> IncidentTicket:
    return IncidentTicket(
        id=ticket_id,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        environment="production",
        service="api",
        title=f"Incident {ticket_id}",
        description="Checkout requests are timing out.",
        resolution_summary="",
        tags=["timeout"],
        severity=2,
    )


def _settings() -> Settings:
    return Settings(database_url="postgresql://test/db")


class _FakeTicketRepository:
    """Satisfies the TicketRepository protocol; only search_fts is exercised."""

    def __init__(self, fts: list[IncidentTicket] | None = None) -> None:
        self._fts = fts or []

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        raise NotImplementedError

    async def get_embedding_meta(self, ticket_id: int) -> TicketEmbeddingMeta | None:
        raise NotImplementedError

    async def search_fts(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        return list(self._fts)

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
        raise NotImplementedError


def _hybrid_search_service(candidates: list[IncidentTicket]) -> TicketHybridSearchService:
    return TicketHybridSearchService(
        ticket_repository=_FakeTicketRepository(fts=candidates),
        embedding_runtime=None,
    )


class _FakeAiProviderRegistry:
    def get_provider(self, provider_id: str) -> AiProviderDefinition:
        return _PROVIDER


class _FakeAiModelBindingResolver:
    def resolve_binding(self) -> AiModelBinding:
        return _BINDING


class _FakeChatClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[tuple[list[ChatMessage], ChatOptions | None]] = []

    async def get_response(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        self.calls.append((list(messages), options))
        return self.response_text


class _FakeChatClientFactory:
    def __init__(self, chat_client: _FakeChatClient) -> None:
        self._chat_client = chat_client

    def create_client(
        self,
        binding: AiModelBinding,
        provider: AiProviderDefinition,
    ) -> _FakeChatClient:
        return self._chat_client


def _service(
    *,
    candidates: list[IncidentTicket],
    response_text: str,
) -> SearchAssistService:
    return SearchAssistService(
        _hybrid_search_service(candidates),
        _FakeAiProviderRegistry(),
        _FakeAiModelBindingResolver(),
        _FakeChatClientFactory(_FakeChatClient(response_text)),
        SearchAssistPromptBuilder(),
        _settings(),
    )


@pytest.mark.asyncio
async def test_assist_returns_no_results_message_when_no_candidates() -> None:
    service = _service(candidates=[], response_text="{}")

    response = await service.assist(AssistRequest(question="Why is checkout failing?"))

    assert response.candidate_count == 0
    assert response.relevant_incidents == []
    assert "could not find any incidents" in response.customer_draft_response


@pytest.mark.asyncio
async def test_assist_happy_path_with_relevant_incidents() -> None:
    candidates = [_ticket(1), _ticket(2), _ticket(3)]
    draft = {
        "relevant_incidents": [
            {"incident_id": 1, "relevance": "Same timeout symptom."},
        ],
        "next_steps": ["Check upstream latency", "Roll back last deploy"],
        "customer_draft_response": "We're investigating similar checkout timeouts.",
    }
    service = _service(candidates=candidates, response_text=json.dumps(draft))

    response = await service.assist(AssistRequest(question="Why is checkout failing?"))

    assert response.candidate_count == 3
    assert [item.incident_id for item in response.relevant_incidents] == [1]
    assert response.next_steps == draft["next_steps"]
    assert response.customer_draft_response == draft["customer_draft_response"]


@pytest.mark.asyncio
async def test_assist_raises_when_llm_selects_no_relevant_incidents() -> None:
    candidates = [_ticket(1), _ticket(2)]
    draft = {
        "relevant_incidents": [],
        "next_steps": [],
        "customer_draft_response": "Nothing matched closely enough.",
    }
    service = _service(candidates=candidates, response_text=json.dumps(draft))

    with pytest.raises(TicketAssistParseException, match="did not select any relevant"):
        await service.assist(AssistRequest(question="Why is checkout failing?"))


@pytest.mark.asyncio
async def test_assist_raises_when_missing_next_steps_for_relevant_incidents() -> None:
    candidates = [_ticket(1)]
    draft = {
        "relevant_incidents": [{"incident_id": 1, "relevance": "Matches symptom."}],
        "next_steps": [],
        "customer_draft_response": "We're looking into this.",
    }
    service = _service(candidates=candidates, response_text=json.dumps(draft))

    with pytest.raises(TicketAssistParseException, match="missing next_steps"):
        await service.assist(AssistRequest(question="Why is checkout failing?"))
