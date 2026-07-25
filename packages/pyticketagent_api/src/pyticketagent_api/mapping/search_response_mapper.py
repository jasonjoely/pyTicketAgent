"""Map incident tickets to search API responses."""

from __future__ import annotations

from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.models.search_response import SearchResponse
from pyticketagent_api.models.search_result_item import SearchResultItem

_MAX_SNIPPET_LENGTH = 100


class SearchResponseMapper:
    """Build SearchResponse from repository search hits."""

    @staticmethod
    def to_search_response(tickets: list[IncidentTicket]) -> SearchResponse:
        return SearchResponse(
            count=len(tickets),
            results=[
                SearchResultItem(
                    id=ticket.id,
                    title=ticket.title,
                    short_snippet=_to_short_snippet(ticket.description),
                )
                for ticket in tickets
            ],
        )


def _to_short_snippet(description: str) -> str:
    if len(description) <= _MAX_SNIPPET_LENGTH:
        return description
    return description[: _MAX_SNIPPET_LENGTH - 3] + "..."
