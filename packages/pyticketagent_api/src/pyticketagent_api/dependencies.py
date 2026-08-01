"""FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from pyticketagent_core.ai.chat_client_factory import ChatClientFactory
from pyticketagent_core.ai.env_var_ai_model_binding_resolver import (
    EnvVarAiModelBindingResolver,
)
from pyticketagent_core.ai.json_ai_provider_registry import JsonAiProviderRegistry
from pyticketagent_core.assist.search_assist_prompt_builder import (
    SearchAssistPromptBuilder,
)
from pyticketagent_core.assist.ticket_assist_prompt_builder import TicketAssistPromptBuilder
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)

from pyticketagent_api.services.search_assist_service import SearchAssistService
from pyticketagent_api.services.ticket_assist_service import TicketAssistService
from pyticketagent_api.services.ticket_hybrid_search_service import (
    TicketHybridSearchService,
)
from pyticketagent_api.services.ticket_ingest_service import TicketIngestService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_ai_provider_registry(request: Request) -> JsonAiProviderRegistry:
    return request.app.state.ai_provider_registry


def get_embedding_runtime(
    request: Request,
) -> DualSpaceEmbeddingRuntime | None:
    return getattr(request.app.state, "embedding_runtime", None)


def get_ticket_repository(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> TicketRepository:
    return TicketRepository(pool)


def get_ticket_hybrid_search_service(
    repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    embedding_runtime: Annotated[
        DualSpaceEmbeddingRuntime | None, Depends(get_embedding_runtime)
    ],
) -> TicketHybridSearchService:
    return TicketHybridSearchService(
        ticket_repository=repository,
        embedding_runtime=embedding_runtime,
    )


def get_ticket_ingest_service(
    repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    embedding_runtime: Annotated[
        DualSpaceEmbeddingRuntime | None, Depends(get_embedding_runtime)
    ],
) -> TicketIngestService:
    return TicketIngestService(
        repository,
        embedding_runtime=embedding_runtime,
        retry_max_attempts=settings.database_retry_max_attempts,
        retry_initial_delay_ms=settings.database_retry_initial_delay_ms,
        retry_max_delay_ms=settings.database_retry_max_delay_ms,
    )


def get_ticket_assist_service(
    repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    registry: Annotated[JsonAiProviderRegistry, Depends(get_ai_provider_registry)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TicketAssistService:
    binding_resolver = EnvVarAiModelBindingResolver(registry, settings)
    chat_client_factory = ChatClientFactory(settings)
    prompt_builder = TicketAssistPromptBuilder()
    return TicketAssistService(
        repository,
        registry,
        binding_resolver,
        chat_client_factory,
        prompt_builder,
        settings,
    )


def get_search_assist_service(
    hybrid_search_service: Annotated[
        TicketHybridSearchService, Depends(get_ticket_hybrid_search_service)
    ],
    registry: Annotated[JsonAiProviderRegistry, Depends(get_ai_provider_registry)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchAssistService:
    binding_resolver = EnvVarAiModelBindingResolver(registry, settings)
    chat_client_factory = ChatClientFactory(settings)
    prompt_builder = SearchAssistPromptBuilder()
    return SearchAssistService(
        hybrid_search_service,
        registry,
        binding_resolver,
        chat_client_factory,
        prompt_builder,
        settings,
    )
