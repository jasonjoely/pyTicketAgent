"""Orchestrate search-driven assist using the configured LLM."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable

from pyticketagent_core.ai.ai_model_binding_resolver import AiModelBindingResolver
from pyticketagent_core.ai.ai_provider_registry import AiProviderRegistry
from pyticketagent_core.ai.chat_client_factory import ChatClientFactory
from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.assist.llm_response_json_extractor import LlmResponseJsonExtractor
from pyticketagent_core.assist.search_assist_llm_draft import SearchAssistLlmDraft
from pyticketagent_core.assist.search_assist_llm_draft_parser import (
    SearchAssistLlmDraftParser,
)
from pyticketagent_core.assist.search_assist_prompt_builder import (
    SearchAssistPromptBuilder,
)
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.models.assist_request import AssistRequest
from pyticketagent_api.models.relevant_incident import RelevantIncident
from pyticketagent_api.models.search_assist_response import SearchAssistResponse
from pyticketagent_api.services.ticket_assist_parse_exception import (
    TicketAssistParseException,
)
from pyticketagent_api.services.ticket_hybrid_search_service import (
    TicketHybridSearchService,
)

logger = logging.getLogger(__name__)

_MAX_CANDIDATES_FOR_LLM = 10
_TOP_IDS_TO_LOG = 10
_MIN_SEARCH_ASSIST_OUTPUT_TOKENS = 2048

_NO_RESULTS_CUSTOMER_DRAFT = (
    "I could not find any incidents matching your question. "
    "Please provide more details such as the environment, service, error message, "
    "or timeframe so we can locate relevant incidents."
)


class SearchAssistService:
    """Search for matching tickets, then ask the LLM to rank and draft assist."""

    def __init__(
        self,
        hybrid_search_service: TicketHybridSearchService,
        registry: AiProviderRegistry,
        binding_resolver: AiModelBindingResolver,
        chat_client_factory: ChatClientFactory,
        prompt_builder: SearchAssistPromptBuilder,
        settings: Settings,
    ) -> None:
        self._hybrid_search_service = hybrid_search_service
        self._registry = registry
        self._binding_resolver = binding_resolver
        self._chat_client_factory = chat_client_factory
        self._prompt_builder = prompt_builder
        self._settings = settings

    async def assist(self, request: AssistRequest) -> SearchAssistResponse:
        question = request.question.strip()
        filter_ = TicketFilter(
            environment=request.environment,
            service=request.service,
            severity=request.severity,
            tags=request.tags,
            status=request.status,
        )

        self._log_search_input(question, filter_)

        candidates = await self._hybrid_search_service.search(
            search_text=question,
            filter_=filter_,
            embedding_space=request.embedding_space,
            limit=_MAX_CANDIDATES_FOR_LLM,
        )
        self._log_search_output(candidates)

        if not candidates:
            self._log_decision(accepted=True, incident_ids=[], reason="no_candidates")
            return self._build_response(0, [], [], _NO_RESULTS_CUSTOMER_DRAFT)

        capped_candidates = candidates[:_MAX_CANDIDATES_FOR_LLM]
        candidate_ids = {ticket.id for ticket in capped_candidates}

        binding = self._binding_resolver.resolve_binding()
        provider = self._registry.get_provider(binding.provider_id)
        client = self._chat_client_factory.create_client(binding, provider)
        messages = self._prompt_builder.build_messages(question, capped_candidates)
        max_output_tokens = max(
            self._settings.max_output_tokens,
            _MIN_SEARCH_ASSIST_OUTPUT_TOKENS,
        )
        options = ChatOptions(max_output_tokens=max_output_tokens)

        self._log_prompt(binding.provider_id, binding.model, messages)

        started_at = time.monotonic()
        response_text = await client.get_response(messages, options)
        latency_ms = round((time.monotonic() - started_at) * 1000)
        self._log_response(response_text, latency_ms)

        try:
            draft = self._parse_draft(response_text, candidate_ids)

            relevant_incidents = [
                RelevantIncident(
                    incident_id=item.incident_id,
                    relevance=item.relevance,
                )
                for item in draft.relevant_incidents
            ]

            api_response = self._build_response(
                len(candidates),
                relevant_incidents,
                draft.next_steps,
                draft.customer_draft_response,
            )
            self._validate_api_response(api_response, len(candidates))
        except TicketAssistParseException as ex:
            self._log_decision(accepted=False, incident_ids=[], reason=str(ex))
            raise

        self._log_decision(
            accepted=True,
            incident_ids=[incident.incident_id for incident in relevant_incidents],
            reason=None,
        )
        return api_response

    @staticmethod
    def _build_response(
        candidate_count: int,
        relevant_incidents: list[RelevantIncident],
        next_steps: list[str],
        customer_draft_response: str,
    ) -> SearchAssistResponse:
        return SearchAssistResponse(
            candidate_count=candidate_count,
            relevant_incidents=relevant_incidents,
            next_steps=next_steps,
            customer_draft_response=customer_draft_response,
        )

    def _log_search_input(self, query: str, filter_: TicketFilter) -> None:
        logger.info(
            "assist.search_input query=%r",
            query,
            extra={
                "event": "assist.search_input",
                "query": query,
                "environment": filter_.environment,
                "service": filter_.service,
                "severity": filter_.severity,
                "tags": list(filter_.tags) if filter_.tags else [],
            },
        )

    def _log_search_output(self, candidates: list[IncidentTicket]) -> None:
        top_ids = [ticket.id for ticket in candidates[:_TOP_IDS_TO_LOG]]
        logger.info(
            "assist.search_output hit_count=%d top_ids=%s",
            len(candidates),
            top_ids,
            extra={
                "event": "assist.search_output",
                "hit_count": len(candidates),
                "top_ids": top_ids,
            },
        )

    def _log_prompt(
        self,
        provider_id: str,
        model: str,
        messages: Iterable[ChatMessage],
    ) -> None:
        rendered = [
            {"role": message.role.value, "content": message.content}
            for message in messages
        ]
        logger.info(
            "assist.prompt provider=%s model=%s messages=%d",
            provider_id,
            model,
            len(rendered),
            extra={
                "event": "assist.prompt",
                "provider": provider_id,
                "model": model,
                "messages": rendered,
            },
        )

    def _log_response(self, response_text: str, latency_ms: int) -> None:
        logger.info(
            "assist.response latency_ms=%d",
            latency_ms,
            extra={
                "event": "assist.response",
                "latency_ms": latency_ms,
                "response_text": response_text,
            },
        )

    def _log_decision(
        self,
        accepted: bool,
        incident_ids: Iterable[int],
        reason: str | None,
    ) -> None:
        ids = list(incident_ids)
        logger.info(
            "assist.decision accepted=%s selected_incident_ids=%s reason=%s",
            accepted,
            ids,
            reason,
            extra={
                "event": "assist.decision",
                "accepted": accepted,
                "selected_incident_ids": ids,
                "reason": reason,
            },
        )

    def _parse_draft(
        self,
        response_text: str,
        candidate_ids: set[int],
    ) -> SearchAssistLlmDraft:
        if not response_text or not response_text.strip():
            logger.error("LLM returned an empty response for search assist.")
            raise TicketAssistParseException("LLM returned an empty response.")

        json_text = LlmResponseJsonExtractor.extract_json(response_text.strip())

        try:
            draft = SearchAssistLlmDraftParser.parse(json_text, candidate_ids)
        except json.JSONDecodeError as ex:
            raise TicketAssistParseException(
                "LLM response was not valid JSON."
            ) from ex

        relevant_incidents = draft.relevant_incidents

        if len(relevant_incidents) > 5:
            raise TicketAssistParseException(
                "LLM response contains more than 5 relevant_incidents."
            )

        if candidate_ids and not relevant_incidents:
            raise TicketAssistParseException(
                "LLM did not select any relevant incidents from the candidate list. "
                "Ensure the response uses relevant_incidents with incident_id values "
                "from the provided candidates."
            )

        for incident in relevant_incidents:
            if incident.incident_id not in candidate_ids:
                raise TicketAssistParseException(
                    f"LLM cited incident_id {incident.incident_id} "
                    "which is not in the candidate list."
                )
            if not incident.relevance.strip():
                raise TicketAssistParseException(
                    "LLM response contains a relevant_incident with empty relevance."
                )

        if relevant_incidents:
            if not draft.next_steps:
                raise TicketAssistParseException(
                    "LLM response is missing next_steps."
                )
            if not draft.customer_draft_response.strip():
                raise TicketAssistParseException(
                    "LLM response is missing customer_draft_response."
                )
        elif not draft.customer_draft_response.strip():
            raise TicketAssistParseException(
                "LLM response must include customer_draft_response asking for more "
                "information when no incidents are relevant."
            )

        return draft

    @staticmethod
    def _validate_api_response(
        response: SearchAssistResponse,
        candidate_count: int,
    ) -> None:
        if response.candidate_count != candidate_count:
            raise TicketAssistParseException(
                f"Response candidate_count ({response.candidate_count}) "
                f"does not match search results ({candidate_count})."
            )

        if candidate_count > 0 and not response.relevant_incidents:
            raise TicketAssistParseException(
                "Response is missing relevant_incidents despite search candidates "
                "being available."
            )

        if response.relevant_incidents and not response.next_steps:
            raise TicketAssistParseException("Response is missing next_steps.")

        if not response.customer_draft_response.strip():
            raise TicketAssistParseException(
                "Response is missing customer_draft_response."
            )
