"""GET /search endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery

from pyticketagent_api.dependencies import get_ticket_repository
from pyticketagent_api.mapping.search_response_mapper import SearchResponseMapper
from pyticketagent_api.models.search_response import SearchResponse

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search incidents",
    description=(
        "Full-text search across incident titles, descriptions, and resolution summaries. "
        "Supports optional filters for environment, service, severity, and comma-separated tags."
    ),
    responses={400: {"description": "Query parameter 'q' is missing or blank"}},
)
async def search(
    ticket_repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    q: Annotated[
        str | None, Query(description="Full-text search query. Required.")
    ] = None,
    environment: Annotated[
        str | None,
        Query(description="Filter by deployment environment (e.g. production, staging)."),
    ] = None,
    service: Annotated[
        str | None, Query(description="Filter by service name.")
    ] = None,
    severity: Annotated[
        int | None, Query(description="Filter by severity level (1-5).")
    ] = None,
    tags: Annotated[
        str | None,
        Query(
            description="Comma-separated list of tags; all specified tags must match."
        ),
    ] = None,
) -> SearchResponse | JSONResponse:
    if q is None or not q.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Query parameter 'q' is required."},
        )

    filter_ = TicketFilter(
        environment=environment,
        service=service,
        severity=severity,
        tags=_parse_tags(tags),
    )
    tickets = await ticket_repository.search(
        TicketSearchQuery(search_text=q, filter=filter_)
    )
    return SearchResponseMapper.to_search_response(tickets)


def _parse_tags(tags: str | None) -> list[str] | None:
    if tags is None or not tags.strip():
        return None

    parsed = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return parsed or None
