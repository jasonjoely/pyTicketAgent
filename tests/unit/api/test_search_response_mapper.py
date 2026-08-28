"""Tests for search response mapping to full tickets."""

from datetime import datetime, timezone

from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_core.tickets.ticket_state import TicketState
from pyticketagent_api.mapping.search_response_mapper import SearchResponseMapper


def test_to_search_response_returns_full_tickets() -> None:
    ticket = IncidentTicket(
        id=42,
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        environment="staging",
        service="payments",
        title="DB lock",
        description="Long description that would previously be truncated",
        resolution_summary="Killed blocker",
        tags=["postgres", "locks"],
        severity=3,
        status=TicketState.RESOLVED,
    )

    response = SearchResponseMapper.to_search_response([ticket])
    payload = response.model_dump(mode="json")

    assert payload["count"] == 1
    assert payload["results"][0]["id"] == 42
    assert payload["results"][0]["description"] == ticket.description
    assert payload["results"][0]["resolution_summary"] == "Killed blocker"
    assert payload["results"][0]["tags"] == ["postgres", "locks"]
    assert "short_snippet" not in payload["results"][0]
