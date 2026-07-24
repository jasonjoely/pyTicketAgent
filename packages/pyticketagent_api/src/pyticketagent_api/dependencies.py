"""FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import Depends, Request

from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.ticket_repository import TicketRepository

from pyticketagent_api.services.ticket_ingest_service import TicketIngestService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_ticket_repository(
    pool: Annotated[asyncpg.Pool, Depends(get_pool)],
) -> TicketRepository:
    return TicketRepository(pool)


def get_ticket_ingest_service(
    repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TicketIngestService:
    return TicketIngestService(
        repository,
        retry_max_attempts=settings.database_retry_max_attempts,
        retry_initial_delay_ms=settings.database_retry_initial_delay_ms,
        retry_max_delay_ms=settings.database_retry_max_delay_ms,
    )
