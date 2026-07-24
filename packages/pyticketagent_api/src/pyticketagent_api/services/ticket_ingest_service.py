"""Ingest service: validate tickets and upsert with soft-fail semantics."""

from __future__ import annotations

import logging

from pyticketagent_core.data.database_transient_error_retry import execute_with_retry
from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.models.incident_ticket_request import IncidentTicketRequest
from pyticketagent_api.models.ingest_counts import IngestCounts
from pyticketagent_api.models.ingest_response import IngestResponse
from pyticketagent_api.models.skipped_ticket_item import SkippedTicketItem

logger = logging.getLogger(__name__)


class TicketIngestService:
    """Accepts a batch of ticket requests and upserts valid ones."""

    def __init__(
        self,
        ticket_repository: TicketRepository,
        *,
        retry_max_attempts: int = 3,
        retry_initial_delay_ms: int = 200,
        retry_max_delay_ms: int = 2000,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._retry_max_attempts = retry_max_attempts
        self._retry_initial_delay_ms = retry_initial_delay_ms
        self._retry_max_delay_ms = retry_max_delay_ms

    async def ingest(self, tickets: list[IncidentTicketRequest]) -> IngestResponse:
        counts = IngestCounts()
        skipped: list[SkippedTicketItem] = []

        for request in tickets:
            ticket, validation_reason = _try_validate(request)
            if ticket is None:
                counts.skipped += 1
                skipped.append(
                    SkippedTicketItem(id=request.id, reason=validation_reason)
                )
                logger.warning(
                    "Skipping ticket %s: %s", request.id, validation_reason
                )
                continue

            try:
                outcome = await execute_with_retry(
                    lambda t=ticket: self._ticket_repository.upsert(t),
                    max_attempts=self._retry_max_attempts,
                    initial_delay_ms=self._retry_initial_delay_ms,
                    max_delay_ms=self._retry_max_delay_ms,
                )
                if outcome == UpsertOutcome.CREATED:
                    counts.ingested += 1
                else:
                    counts.updated += 1
            except Exception as ex:
                counts.skipped += 1
                reason = f"Database error: {ex}"
                skipped.append(SkippedTicketItem(id=request.id, reason=reason))
                logger.error(
                    "Skipping ticket %s after database failure",
                    request.id,
                    exc_info=ex,
                )

        return IngestResponse(counts=counts, skipped=skipped)


def _try_validate(
    request: IncidentTicketRequest,
) -> tuple[IncidentTicket | None, str]:
    if request.id <= 0:
        return None, "Ticket id must be greater than zero."

    if not request.environment or not request.environment.strip():
        return None, "Environment is required."

    if not request.service or not request.service.strip():
        return None, "Service is required."

    if not request.title or not request.title.strip():
        return None, "Title is required."

    if not request.description or not request.description.strip():
        return None, "Description is required."

    severity = 0 if request.severity is None else request.severity
    if severity < 0:
        return None, "Severity must be non-negative."

    ticket = IncidentTicket(
        id=request.id,
        created_at=request.created_at,
        environment=request.environment.strip(),
        service=request.service.strip(),
        title=request.title.strip(),
        description=request.description.strip(),
        resolution_summary=request.resolution_summary or "",
        tags=list(request.tags) if request.tags is not None else [],
        severity=severity,
    )
    return ticket, ""
