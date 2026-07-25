"""Full-text search query with optional filters."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.data.ticket_filter import TicketFilter


@dataclass(frozen=True, slots=True)
class TicketSearchQuery:
    """Search text plus optional structured filters."""

    search_text: str
    filter: TicketFilter | None = None
