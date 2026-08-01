"""Map incident tickets to search API responses."""

from __future__ import annotations

from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.models.search_response import SearchResponse


class SearchResponseMapper:
    """Build SearchResponse from hybrid search hits."""

    @staticmethod
    def to_search_response(tickets: list[IncidentTicket]) -> SearchResponse:
        return SearchResponse(count=len(tickets), results=tickets)
