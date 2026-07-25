"""LLM draft item for a relevant incident."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelevantIncidentDraft:
    """One incident selected by the search-assist LLM."""

    incident_id: int
    relevance: str
