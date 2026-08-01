"""Orchestrate search-driven assist using the configured LLM."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable

from pyticketagent_core.ai.chat_client_factory import ChatClientFactory
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.ai.env_var_ai_model_binding_resolver import (
    EnvVarAiModelBindingResolver,
)
from pyticketagent_core.ai.json_ai_provider_registry import JsonAiProviderRegistry
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
        registry: JsonAiProviderRegistry,
        binding_resolver: EnvVarAiModelBindingResolver,
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
            self._log_selected_incident_ids([])
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

        logger.info(
            "Assisting with search question using %s/%s",
            binding.provider_id,
            binding.model,
        )

        response_text = await client.get_response(messages, options)
        draft = self._parse_draft(response_text, candidate_ids)

        relevant_incidents = [
            RelevantIncident(
                incident_id=item.incident_id,
                relevance=item.relevance,
            )
            for item in draft.relevant_incidents
        ]
        self._log_selected_incident_ids(
            incident.incident_id for incident in relevant_incidents
        )

        api_response = self._build_response(
            len(candidates),
            relevant_incidents,
            draft.next_steps,
            draft.customer_draft_response,
        )
        self._validate_api_response(api_response, len(candidates))
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
        tags = ",".join(filter_.tags) if filter_.tags else ""
        logger.info(
            "tool:search input summary. Query: %s, Environment: %s, Service: %s, "
            "Severity: %s, Tags: %s",
            query,
            filter_.environment or "",
            filter_.service or "",
            "" if filter_.severity is None else str(filter_.severity),
            tags,
        )

    def _log_search_output(self, candidates: list[IncidentTicket]) -> None:
        top_ids = ",".join(
            str(ticket.id) for ticket in candidates[:_TOP_IDS_TO_LOG]
        )
        logger.info(
            "tool:search output summary. HitCount: %s, TopIds: %s",
            len(candidates),
            top_ids,
        )

    def _log_selected_incident_ids(self, incident_ids: Iterable[int]) -> None:
        ids = ",".join(str(incident_id) for incident_id in incident_ids)
        logger.info("Selected incident IDs. SelectedIncidentIds: %s", ids)

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
            logger.error(
                "Failed to parse LLM search assist response: %s",
                response_text,
            )
            raise TicketAssistParseException(
                "LLM response was not valid JSON."
            ) from ex

        relevant_incidents = draft.relevant_incidents

        if len(relevant_incidents) > 5:
            raise TicketAssistParseException(
                "LLM response contains more than 5 relevant_incidents."
            )

        if candidate_ids and not relevant_incidents:
            logger.error(
                "LLM returned no relevant_incidents despite %s candidates. Response: %s",
                len(candidate_ids),
                response_text,
            )
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
