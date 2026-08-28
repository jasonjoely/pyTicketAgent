"""Optional filters applied to ticket queries."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.tickets.ticket_state import TicketState


@dataclass(frozen=True, slots=True)
class TicketFilter:
    """Filter criteria for ticket list/search queries."""

    environment: str | None = None
    service: str | None = None
    tags: list[str] | None = None
    severity: int | None = None
    status: TicketState | None = None
