"""Repository for incident ticket persistence via asyncpg."""

from __future__ import annotations

import asyncpg

from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

_SELECT_COLUMNS = """
    id,
    created_at,
    environment,
    service,
    title,
    description,
    resolution_summary,
    tags,
    severity
"""

_UPSERT_SQL = """
    INSERT INTO tickets (
        id, created_at, environment, service, title, description,
        resolution_summary, tags, severity
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ON CONFLICT (id) DO UPDATE SET
        created_at         = EXCLUDED.created_at,
        environment        = EXCLUDED.environment,
        service            = EXCLUDED.service,
        title              = EXCLUDED.title,
        description        = EXCLUDED.description,
        resolution_summary = EXCLUDED.resolution_summary,
        tags               = EXCLUDED.tags,
        severity           = EXCLUDED.severity
    RETURNING (xmax = 0) AS inserted
"""

_GET_BY_ID_SQL = f"""
    SELECT {_SELECT_COLUMNS}
    FROM tickets
    WHERE id = $1
"""


class TicketRepository:
    """Data access for the ``tickets`` table."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        """Return the ticket with the given id, or None if not found."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(_GET_BY_ID_SQL, ticket_id)

        if row is None:
            return None

        return _row_to_ticket(row)

    async def upsert(self, ticket: IncidentTicket) -> UpsertOutcome:
        """Insert or update a ticket by id. Returns Created or Updated."""
        async with self._pool.acquire() as connection:
            inserted = await connection.fetchval(
                _UPSERT_SQL,
                ticket.id,
                ticket.created_at,
                ticket.environment,
                ticket.service,
                ticket.title,
                ticket.description,
                ticket.resolution_summary,
                ticket.tags,
                ticket.severity,
            )

        return UpsertOutcome.CREATED if inserted else UpsertOutcome.UPDATED


def _row_to_ticket(row: asyncpg.Record) -> IncidentTicket:
    tags = row["tags"]
    return IncidentTicket(
        id=row["id"],
        created_at=row["created_at"],
        environment=row["environment"],
        service=row["service"],
        title=row["title"],
        description=row["description"],
        resolution_summary=row["resolution_summary"],
        tags=list(tags) if tags is not None else [],
        severity=row["severity"],
    )
