"""GET /incidents/{id} endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

from pyticketagent_api.dependencies import get_ticket_repository

router = APIRouter(tags=["Incidents"])


@router.get(
    "/incidents/{id}",
    response_model=IncidentTicket,
    summary="Get incident by ID",
    description=(
        "Returns the full incident ticket for the given ID, including title, description, "
        "resolution summary, tags, and severity."
    ),
    responses={404: {"description": "Incident not found"}},
)
async def get_incident_by_id(
    id: Annotated[int, Path(description="Unique incident ticket identifier.")],
    ticket_repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
) -> IncidentTicket:
    ticket = await ticket_repository.get_by_id(id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ticket
