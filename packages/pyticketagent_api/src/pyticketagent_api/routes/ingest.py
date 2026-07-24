"""POST /ingest endpoint."""

from fastapi import APIRouter, Depends

from pyticketagent_api.dependencies import get_ticket_ingest_service
from pyticketagent_api.models.incident_ticket_request import IncidentTicketRequest
from pyticketagent_api.models.ingest_response import IngestResponse
from pyticketagent_api.services.ticket_ingest_service import TicketIngestService

router = APIRouter(tags=["Ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest incident tickets",
    description=(
        "Accepts a JSON array of incident tickets and upserts them into the database. "
        "Returns counts of ingested, updated, and skipped tickets, plus details for any "
        "skipped entries."
    ),
)
async def ingest(
    tickets: list[IncidentTicketRequest],
    ingest_service: TicketIngestService = Depends(get_ticket_ingest_service),
) -> IngestResponse:
    return await ingest_service.ingest(tickets)
