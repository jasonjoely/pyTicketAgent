"""Assist endpoints (ticket assist-by-id and search assist)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse, Response

from pyticketagent_core.configuration.settings import Settings

from pyticketagent_api.dependencies import (
    get_search_assist_service,
    get_settings,
    get_ticket_assist_service,
)
from pyticketagent_api.models.assist_request import AssistRequest
from pyticketagent_api.models.search_assist_response import SearchAssistResponse
from pyticketagent_api.models.ticket_assist_response import TicketAssistResponse
from pyticketagent_api.services.llm_setup_help import LlmSetupHelp
from pyticketagent_api.services.search_assist_service import SearchAssistService
from pyticketagent_api.services.ticket_assist_parse_exception import (
    TicketAssistParseException,
)
from pyticketagent_api.services.ticket_assist_service import TicketAssistService

router = APIRouter(tags=["Assist"])


@router.get(
    "/incidents/{id}/assist",
    response_model=TicketAssistResponse,
    summary="Get AI assist for an incident",
    description=(
        "Uses an LLM to analyze the specified incident and return recommended next steps "
        "plus a draft customer response."
    ),
    responses={
        404: {"description": "Incident not found"},
        502: {"description": "LLM response could not be parsed"},
        503: {"description": "LLM configuration missing/invalid or request timed out"},
    },
)
async def ticket_assist(
    id: Annotated[int, Path(description="Unique incident ticket identifier.")],
    assist_service: Annotated[TicketAssistService, Depends(get_ticket_assist_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TicketAssistResponse | Response:
    try:
        response = await assist_service.assist(id)
    except ValueError as ex:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": LlmSetupHelp.enrich(str(ex))},
        )
    except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": LlmSetupHelp.timeout_message(
                    settings.llm_request_timeout_seconds
                )
            },
        )
    except TicketAssistParseException as ex:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": str(ex)},
        )

    if response is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return response


@router.post(
    "/assist",
    response_model=SearchAssistResponse,
    summary="Get AI assist from a question",
    description=(
        "Hybrid-searches for relevant incidents matching the question and filters "
        "(full-text + semantic fused with RRF), then uses an LLM to identify the most "
        "relevant matches and return next steps plus a draft customer response. "
        "Optional embedding_space selects the semantic vector column "
        "(defaults to embedding_providers.json defaultSearchSpace)."
    ),
    responses={
        400: {"description": "Field 'question' is missing or blank"},
        502: {"description": "LLM response could not be parsed"},
        503: {"description": "LLM configuration missing/invalid or request timed out"},
    },
)
async def search_assist(
    request: AssistRequest,
    search_assist_service: Annotated[
        SearchAssistService, Depends(get_search_assist_service)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchAssistResponse | JSONResponse:
    if not request.question or not request.question.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Field 'question' is required."},
        )

    try:
        return await search_assist_service.assist(request)
    except ValueError as ex:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": LlmSetupHelp.enrich(str(ex))},
        )
    except (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": LlmSetupHelp.timeout_message(
                    settings.llm_request_timeout_seconds
                )
            },
        )
    except TicketAssistParseException as ex:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"error": str(ex)},
        )
