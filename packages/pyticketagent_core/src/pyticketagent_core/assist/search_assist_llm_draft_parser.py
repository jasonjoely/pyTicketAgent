"""Tolerant parser for search-assist LLM JSON drafts."""

from __future__ import annotations

import json
from typing import Any

from pyticketagent_core.assist.relevant_incident_draft import RelevantIncidentDraft
from pyticketagent_core.assist.search_assist_llm_draft import SearchAssistLlmDraft

_DEFAULT_RELEVANCE = "Listed as relevant to the question."

_RELEVANT_INCIDENTS_PROPERTY_NAMES = (
    "relevant_incidents",
    "relevantIncidents",
    "incidents",
)
_NEXT_STEPS_PROPERTY_NAMES = ("next_steps", "nextSteps")
_CUSTOMER_DRAFT_PROPERTY_NAMES = (
    "customer_draft_response",
    "customerDraftResponse",
)
_INCIDENT_ID_PROPERTY_NAMES = ("incident_id", "incidentId", "id")
_RELEVANCE_PROPERTY_NAMES = ("relevance", "reason", "explanation")


class SearchAssistLlmDraftParser:
    """Parse LLM JSON with snake_case / camelCase / alternate key aliases."""

    @staticmethod
    def parse(json_text: str, candidate_ids: set[int]) -> SearchAssistLlmDraft:
        root = json.loads(json_text)
        if not isinstance(root, dict):
            raise json.JSONDecodeError("Expected a JSON object", json_text, 0)

        relevant_incidents = _parse_relevant_incidents(root, candidate_ids)
        next_steps = _parse_string_array(root, _NEXT_STEPS_PROPERTY_NAMES)
        customer_draft = _parse_string(root, _CUSTOMER_DRAFT_PROPERTY_NAMES)

        return SearchAssistLlmDraft(
            relevant_incidents=relevant_incidents,
            next_steps=next_steps,
            customer_draft_response=customer_draft or "",
        )


def _parse_relevant_incidents(
    root: dict[str, Any],
    candidate_ids: set[int],
) -> list[RelevantIncidentDraft]:
    incidents_value = _try_get_property(root, _RELEVANT_INCIDENTS_PROPERTY_NAMES)
    if not isinstance(incidents_value, list):
        return []

    results: list[RelevantIncidentDraft] = []
    for item in incidents_value:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            if item in candidate_ids:
                results.append(
                    RelevantIncidentDraft(
                        incident_id=item,
                        relevance=_DEFAULT_RELEVANCE,
                    )
                )
            continue

        if not isinstance(item, dict):
            continue

        incident_id = _parse_incident_id(item)
        if incident_id is None or incident_id not in candidate_ids:
            continue

        relevance = _parse_string(item, _RELEVANCE_PROPERTY_NAMES)
        results.append(
            RelevantIncidentDraft(
                incident_id=incident_id,
                relevance=(
                    _DEFAULT_RELEVANCE
                    if relevance is None or not relevance.strip()
                    else relevance.strip()
                ),
            )
        )

    return results


def _parse_incident_id(item: dict[str, Any]) -> int | None:
    for property_name in _INCIDENT_ID_PROPERTY_NAMES:
        value = item.get(property_name)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return None


def _parse_string_array(
    root: dict[str, Any],
    property_names: tuple[str, ...],
) -> list[str]:
    value = _try_get_property(root, property_names)
    if not isinstance(value, list):
        return []

    results: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            results.append(item.strip())
    return results


def _parse_string(
    root: dict[str, Any],
    property_names: tuple[str, ...],
) -> str | None:
    value = _try_get_property(root, property_names)
    if isinstance(value, str):
        return value
    return None


def _try_get_property(
    element: dict[str, Any],
    property_names: tuple[str, ...],
) -> Any | None:
    for property_name in property_names:
        if property_name in element:
            return element[property_name]
    return None
