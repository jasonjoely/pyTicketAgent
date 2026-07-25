"""Orchestrate ticket assist-by-id using the configured LLM."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from pyticketagent_core.ai.chat_client_factory import ChatClientFactory
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.ai.env_var_ai_model_binding_resolver import (
    EnvVarAiModelBindingResolver,
)
from pyticketagent_core.ai.json_ai_provider_registry import JsonAiProviderRegistry
from pyticketagent_core.assist.llm_response_json_extractor import LlmResponseJsonExtractor
from pyticketagent_core.assist.ticket_assist_llm_draft import TicketAssistLlmDraft
from pyticketagent_core.assist.ticket_assist_prompt_builder import TicketAssistPromptBuilder
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_repository import TicketRepository

from pyticketagent_api.models.ticket_assist_response import TicketAssistResponse
from pyticketagent_api.services.ticket_assist_parse_exception import (
    TicketAssistParseException,
)

logger = logging.getLogger(__name__)


class TicketAssistService:
    """Load a ticket and ask the LLM for next steps + a customer draft."""

    def __init__(
        self,
        ticket_repository: TicketRepository,
        registry: JsonAiProviderRegistry,
        binding_resolver: EnvVarAiModelBindingResolver,
        chat_client_factory: ChatClientFactory,
        prompt_builder: TicketAssistPromptBuilder,
        settings: Settings,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._registry = registry
        self._binding_resolver = binding_resolver
        self._chat_client_factory = chat_client_factory
        self._prompt_builder = prompt_builder
        self._settings = settings

    async def assist(self, ticket_id: int) -> TicketAssistResponse | None:
        ticket = await self._ticket_repository.get_by_id(ticket_id)
        if ticket is None:
            return None

        binding = self._binding_resolver.resolve_binding()
        provider = self._registry.get_provider(binding.provider_id)
        client = self._chat_client_factory.create_client(binding, provider)
        messages = self._prompt_builder.build_messages(ticket)
        options = ChatOptions(max_output_tokens=self._settings.max_output_tokens)

        logger.info(
            "Assisting with ticket %s using %s/%s",
            ticket_id,
            binding.provider_id,
            binding.model,
        )

        response_text = await client.get_response(messages, options)
        draft = self._parse_draft(response_text)

        return TicketAssistResponse(
            ticket_id=ticket.id,
            next_steps=draft.next_steps,
            customer_draft_response=draft.customer_draft_response,
            provider=binding.provider_id,
            model=binding.model,
        )

    def _parse_draft(self, response_text: str) -> TicketAssistLlmDraft:
        if not response_text or not response_text.strip():
            logger.error("LLM returned an empty response for ticket assist.")
            raise TicketAssistParseException("LLM returned an empty response.")

        json_text = LlmResponseJsonExtractor.extract_json(response_text.strip())
        try:
            draft = TicketAssistLlmDraft.model_validate_json(json_text)
        except ValidationError as ex:
            logger.error(
                "Failed to parse LLM ticket assist response: %s",
                response_text,
            )
            raise TicketAssistParseException(
                "LLM response was not valid JSON."
            ) from ex

        if not draft.next_steps:
            raise TicketAssistParseException("LLM response is missing next_steps.")
        if not draft.customer_draft_response.strip():
            raise TicketAssistParseException(
                "LLM response is missing customer_draft_response."
            )
        return draft
