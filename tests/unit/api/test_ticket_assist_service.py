"""Tests for TicketAssistService."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind
from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.assist.ticket_assist_prompt_builder import TicketAssistPromptBuilder
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.services.ticket_assist_parse_exception import (
    TicketAssistParseException,
)
from pyticketagent_api.services.ticket_assist_service import TicketAssistService

_PROVIDER = AiProviderDefinition(id="fake-provider", kind=AiProviderKind.OLLAMA)
_BINDING = AiModelBinding(provider_id="fake-provider", model="fake-model")


def _ticket(ticket_id: int = 1) -> IncidentTicket:
    return IncidentTicket(
        id=ticket_id,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        environment="production",
        service="api",
        title="Timeout on checkout",
        description="Checkout requests are timing out.",
        resolution_summary="",
        tags=["timeout"],
        severity=2,
    )


def _settings() -> Settings:
    return Settings(database_url="postgresql://test/db")


class _FakeTicketRepository:
    def __init__(self, ticket: IncidentTicket | None) -> None:
        self._ticket = ticket

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        return self._ticket

    async def get_embedding_meta(self, ticket_id: int) -> TicketEmbeddingMeta | None:
        raise NotImplementedError

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
        raise NotImplementedError


class _FakeAiProviderRegistry:
    def __init__(self, provider: AiProviderDefinition = _PROVIDER) -> None:
        self._provider = provider

    def get_provider(self, provider_id: str) -> AiProviderDefinition:
        return self._provider


class _FakeAiModelBindingResolver:
    def __init__(self, binding: AiModelBinding = _BINDING) -> None:
        self._binding = binding

    def resolve_binding(self) -> AiModelBinding:
        return self._binding


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
    ticket: IncidentTicket | None,
    response_text: str,
) -> TicketAssistService:
    return TicketAssistService(
        _FakeTicketRepository(ticket),
        _FakeAiProviderRegistry(),
        _FakeAiModelBindingResolver(),
        _FakeChatClientFactory(_FakeChatClient(response_text)),
        TicketAssistPromptBuilder(),
        _settings(),
    )


@pytest.mark.asyncio
async def test_assist_returns_response_for_valid_llm_json() -> None:
    draft = {
        "next_steps": ["Check logs", "Roll back deploy"],
        "customer_draft_response": "We're investigating the checkout timeout.",
    }
    service = _service(ticket=_ticket(42), response_text=json.dumps(draft))

    response = await service.assist(42)

    assert response is not None
    assert response.ticket_id == 42
    assert response.next_steps == draft["next_steps"]
    assert response.customer_draft_response == draft["customer_draft_response"]
    assert response.provider == "fake-provider"
    assert response.model == "fake-model"


@pytest.mark.asyncio
async def test_assist_returns_none_when_ticket_not_found() -> None:
    service = _service(ticket=None, response_text="{}")

    response = await service.assist(999)

    assert response is None


@pytest.mark.asyncio
async def test_assist_raises_on_empty_llm_response() -> None:
    service = _service(ticket=_ticket(), response_text="   ")

    with pytest.raises(TicketAssistParseException, match="empty response"):
        await service.assist(1)


@pytest.mark.asyncio
async def test_assist_raises_on_non_json_llm_response() -> None:
    service = _service(ticket=_ticket(), response_text="Sorry, I can't help with that.")

    with pytest.raises(TicketAssistParseException, match="not valid JSON"):
        await service.assist(1)


@pytest.mark.asyncio
async def test_assist_raises_when_llm_response_missing_required_field() -> None:
    draft = {"next_steps": ["Check logs"]}
    service = _service(ticket=_ticket(), response_text=json.dumps(draft))

    with pytest.raises(TicketAssistParseException, match="not valid JSON"):
        await service.assist(1)
