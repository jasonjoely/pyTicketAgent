"""Orchestrate ticket assist-by-id using the configured LLM."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from pydantic import ValidationError

from pyticketagent_core.ai.ai_model_binding_resolver import AiModelBindingResolver
from pyticketagent_core.ai.ai_provider_registry import AiProviderRegistry
from pyticketagent_core.ai.chat_client_factory import ChatClientFactory
from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
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
        registry: AiProviderRegistry,
        binding_resolver: AiModelBindingResolver,
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

        self._log_prompt(ticket_id, binding.provider_id, binding.model, messages)

        started_at = time.monotonic()
        response_text = await client.get_response(messages, options)
        latency_ms = round((time.monotonic() - started_at) * 1000)
        self._log_response(ticket_id, response_text, latency_ms)

        try:
            draft = self._parse_draft(response_text)
        except TicketAssistParseException as ex:
            self._log_decision(ticket_id, accepted=False, reason=str(ex))
            raise

        self._log_decision(ticket_id, accepted=True, reason=None)
        return TicketAssistResponse(
            ticket_id=ticket.id,
            next_steps=draft.next_steps,
            customer_draft_response=draft.customer_draft_response,
            provider=binding.provider_id,
            model=binding.model,
        )

    def _log_prompt(
        self,
        ticket_id: int,
        provider_id: str,
        model: str,
        messages: Iterable[ChatMessage],
    ) -> None:
        rendered = [
            {"role": message.role.value, "content": message.content}
            for message in messages
        ]
        logger.info(
            "assist.prompt ticket_id=%s provider=%s model=%s messages=%d",
            ticket_id,
            provider_id,
            model,
            len(rendered),
            extra={
                "event": "assist.prompt",
                "ticket_id": ticket_id,
                "provider": provider_id,
                "model": model,
                "messages": rendered,
            },
        )

    def _log_response(self, ticket_id: int, response_text: str, latency_ms: int) -> None:
        logger.info(
            "assist.response ticket_id=%s latency_ms=%d",
            ticket_id,
            latency_ms,
            extra={
                "event": "assist.response",
                "ticket_id": ticket_id,
                "latency_ms": latency_ms,
                "response_text": response_text,
            },
        )

    def _log_decision(
        self, ticket_id: int, accepted: bool, reason: str | None
    ) -> None:
        logger.info(
            "assist.decision ticket_id=%s accepted=%s reason=%s",
            ticket_id,
            accepted,
            reason,
            extra={
                "event": "assist.decision",
                "ticket_id": ticket_id,
                "accepted": accepted,
                "reason": reason,
            },
        )

    def _parse_draft(self, response_text: str) -> TicketAssistLlmDraft:
        if not response_text or not response_text.strip():
            logger.error("LLM returned an empty response for ticket assist.")
            raise TicketAssistParseException("LLM returned an empty response.")

        json_text = LlmResponseJsonExtractor.extract_json(response_text.strip())
        try:
            draft = TicketAssistLlmDraft.model_validate_json(json_text)
        except ValidationError as ex:
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
