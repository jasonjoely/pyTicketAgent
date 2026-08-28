"""GET /search endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.tickets.ticket_state import TicketState

from pyticketagent_api.dependencies import get_ticket_hybrid_search_service
from pyticketagent_api.mapping.search_response_mapper import SearchResponseMapper
from pyticketagent_api.models.search_response import SearchResponse
from pyticketagent_api.services.ticket_hybrid_search_service import (
    TicketHybridSearchService,
)

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search incidents",
    description=(
        "Hybrid search (full-text + semantic) across incident titles, descriptions, "
        "and resolution summaries, fused with Reciprocal Rank Fusion. "
        "Supports optional filters for environment, service, severity, and "
        "comma-separated tags. Optional embedding_space selects which vector column "
        "to use for the semantic leg (defaults to embedding_providers.json "
        "defaultSearchSpace)."
    ),
    responses={400: {"description": "Query parameter 'q' is missing or blank"}},
)
async def search(
    hybrid_search_service: Annotated[
        TicketHybridSearchService, Depends(get_ticket_hybrid_search_service)
    ],
    q: Annotated[
        str | None, Query(description="Search query. Required.")
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
    status: Annotated[
        TicketState | None,
        Query(description="Filter by ticket status."),
    ] = None,
    embedding_space: Annotated[
        EmbeddingSpace | None,
        Query(
            description=(
                "Embedding space for the semantic leg (fastembed or ollama). "
                "Omitting uses defaultSearchSpace from config."
            ),
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
        status=status,
    )
    tickets = await hybrid_search_service.search(
        search_text=q,
        filter_=filter_,
        embedding_space=embedding_space,
    )
    return SearchResponseMapper.to_search_response(tickets)


def _parse_tags(tags: str | None) -> list[str] | None:
    if tags is None or not tags.strip():
        return None

    parsed = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return parsed or None
