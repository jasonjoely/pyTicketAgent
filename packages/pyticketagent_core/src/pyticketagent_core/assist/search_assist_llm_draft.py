"""Parsed LLM draft for search assist."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.assist.relevant_incident_draft import RelevantIncidentDraft


@dataclass(frozen=True, slots=True)
class SearchAssistLlmDraft:
    """Expected fields returned by the search-assist prompt."""

    relevant_incidents: list[RelevantIncidentDraft]
    next_steps: list[str]
    customer_draft_response: str
