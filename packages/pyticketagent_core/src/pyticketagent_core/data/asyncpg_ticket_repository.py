"""asyncpg-backed implementation of the ``TicketRepository`` protocol."""

from __future__ import annotations

import asyncpg

from pyticketagent_core.data.ticket_filter import TicketFilter
from pyticketagent_core.data.ticket_search_query import TicketSearchQuery
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.embedding_space_write import EmbeddingSpaceWrite
from pyticketagent_core.embeddings.pgvector_literal import format_pgvector_literal
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embedding_space_meta import (
    TicketEmbeddingSpaceMeta,
)
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
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
        resolution_summary, tags, severity,
        embedding_fastembed, embedding_fastembed_model,
        embedding_fastembed_content_hash, embedding_fastembed_updated_at,
        embedding_ollama, embedding_ollama_model,
        embedding_ollama_content_hash, embedding_ollama_updated_at
    )
    VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9,
        $10::vector, $11, $12, $13,
        $14::vector, $15, $16, $17
    )
    ON CONFLICT (id) DO UPDATE SET
        created_at         = EXCLUDED.created_at,
        environment        = EXCLUDED.environment,
        service            = EXCLUDED.service,
        title              = EXCLUDED.title,
        description        = EXCLUDED.description,
        resolution_summary = EXCLUDED.resolution_summary,
        tags               = EXCLUDED.tags,
        severity           = EXCLUDED.severity,
        embedding_fastembed = CASE
            WHEN $18::boolean THEN EXCLUDED.embedding_fastembed
            ELSE tickets.embedding_fastembed
        END,
        embedding_fastembed_model = CASE
            WHEN $18::boolean THEN EXCLUDED.embedding_fastembed_model
            ELSE tickets.embedding_fastembed_model
        END,
        embedding_fastembed_content_hash = CASE
            WHEN $18::boolean THEN EXCLUDED.embedding_fastembed_content_hash
            ELSE tickets.embedding_fastembed_content_hash
        END,
        embedding_fastembed_updated_at = CASE
            WHEN $18::boolean THEN EXCLUDED.embedding_fastembed_updated_at
            ELSE tickets.embedding_fastembed_updated_at
        END,
        embedding_ollama = CASE
            WHEN $19::boolean THEN EXCLUDED.embedding_ollama
            ELSE tickets.embedding_ollama
        END,
        embedding_ollama_model = CASE
            WHEN $19::boolean THEN EXCLUDED.embedding_ollama_model
            ELSE tickets.embedding_ollama_model
        END,
        embedding_ollama_content_hash = CASE
            WHEN $19::boolean THEN EXCLUDED.embedding_ollama_content_hash
            ELSE tickets.embedding_ollama_content_hash
        END,
        embedding_ollama_updated_at = CASE
            WHEN $19::boolean THEN EXCLUDED.embedding_ollama_updated_at
            ELSE tickets.embedding_ollama_updated_at
        END
    RETURNING (xmax = 0) AS inserted
"""

_GET_BY_ID_SQL = f"""
    SELECT {_SELECT_COLUMNS}
    FROM tickets
    WHERE id = $1
"""

_GET_EMBEDDING_META_SQL = """
    SELECT
        embedding_fastembed_model,
        embedding_fastembed_content_hash,
        (embedding_fastembed IS NOT NULL) AS embedding_fastembed_has_vector,
        embedding_ollama_model,
        embedding_ollama_content_hash,
        (embedding_ollama IS NOT NULL) AS embedding_ollama_has_vector
    FROM tickets
    WHERE id = $1
"""

_EMBEDDING_COLUMN_BY_SPACE = {
    EmbeddingSpace.FASTEMBED: "embedding_fastembed",
    EmbeddingSpace.OLLAMA: "embedding_ollama",
}


class AsyncpgTicketRepository:
    """Data access for the ``tickets`` table, backed by asyncpg."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_id(self, ticket_id: int) -> IncidentTicket | None:
        """Return the ticket with the given id, or None if not found."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(_GET_BY_ID_SQL, ticket_id)

        if row is None:
            return None

        return _row_to_ticket(row)

    async def get_embedding_meta(
        self, ticket_id: int
    ) -> TicketEmbeddingMeta | None:
        """Return embedding metadata for hash-skip decisions, or None if missing."""
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(_GET_EMBEDDING_META_SQL, ticket_id)

        if row is None:
            return None

        return TicketEmbeddingMeta(
            fastembed=TicketEmbeddingSpaceMeta(
                model=row["embedding_fastembed_model"],
                content_hash=row["embedding_fastembed_content_hash"],
                has_vector=bool(row["embedding_fastembed_has_vector"]),
            ),
            ollama=TicketEmbeddingSpaceMeta(
                model=row["embedding_ollama_model"],
                content_hash=row["embedding_ollama_content_hash"],
                has_vector=bool(row["embedding_ollama_has_vector"]),
            ),
        )

    async def search(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        """Full-text search (alias for ``search_fts``)."""
        return await self.search_fts(query)

    async def search_fts(self, query: TicketSearchQuery) -> list[IncidentTicket]:
        """Full-text search ranked by ``ts_rank``, with optional filters/limit."""
        search_text = query.search_text.strip()
        if not search_text:
            return []

        filter_ = query.filter or TicketFilter()
        conditions = ["search_vector @@ plainto_tsquery('english', $1)"]
        args: list[object] = [search_text]
        param_index = 2

        param_index = _append_filter_conditions(
            conditions, args, filter_, param_index
        )

        where_sql = " AND ".join(conditions)
        limit_sql = ""
        if query.limit is not None:
            limit_sql = f" LIMIT ${param_index}"
            args.append(query.limit)

        search_sql = f"""
            SELECT {_SELECT_COLUMNS}
            FROM tickets
            WHERE {where_sql}
            ORDER BY ts_rank(search_vector, plainto_tsquery('english', $1)) DESC,
                     id ASC
            {limit_sql}
        """

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(search_sql, *args)

        return [_row_to_ticket(row) for row in rows]

    async def search_semantic(
        self,
        query_vector: list[float],
        space: EmbeddingSpace,
        filter_: TicketFilter | None = None,
        limit: int | None = None,
    ) -> list[IncidentTicket]:
        """Cosine-distance search against one embedding column."""
        column = _EMBEDDING_COLUMN_BY_SPACE[space]
        filter_ = filter_ or TicketFilter()
        conditions = [f"{column} IS NOT NULL"]
        args: list[object] = [format_pgvector_literal(query_vector)]
        param_index = 2

        param_index = _append_filter_conditions(
            conditions, args, filter_, param_index
        )

        where_sql = " AND ".join(conditions)
        limit_sql = ""
        if limit is not None:
            limit_sql = f" LIMIT ${param_index}"
            args.append(limit)

        search_sql = f"""
            SELECT {_SELECT_COLUMNS}
            FROM tickets
            WHERE {where_sql}
            ORDER BY {column} <=> $1::vector, id ASC
            {limit_sql}
        """

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(search_sql, *args)

        return [_row_to_ticket(row) for row in rows]

    async def upsert(
        self,
        ticket: IncidentTicket,
        embeddings: TicketEmbeddingsWrite | None = None,
    ) -> UpsertOutcome:
        """Insert or update a ticket by id. Returns Created or Updated."""
        write = embeddings or TicketEmbeddingsWrite(
            fastembed=EmbeddingSpaceWrite.preserve(),
            ollama=EmbeddingSpaceWrite.preserve(),
        )

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
                format_pgvector_literal(write.fastembed.vector),
                write.fastembed.model,
                write.fastembed.content_hash,
                write.fastembed.updated_at,
                format_pgvector_literal(write.ollama.vector),
                write.ollama.model,
                write.ollama.content_hash,
                write.ollama.updated_at,
                write.fastembed.update,
                write.ollama.update,
            )

        return UpsertOutcome.CREATED if inserted else UpsertOutcome.UPDATED


def _append_filter_conditions(
    conditions: list[str],
    args: list[object],
    filter_: TicketFilter,
    param_index: int,
) -> int:
    if filter_.environment and filter_.environment.strip():
        conditions.append(f"environment = ${param_index}")
        args.append(filter_.environment)
        param_index += 1

    if filter_.service and filter_.service.strip():
        conditions.append(f"service = ${param_index}")
        args.append(filter_.service)
        param_index += 1

    if filter_.tags:
        conditions.append(f"tags && ${param_index}::text[]")
        args.append(filter_.tags)
        param_index += 1

    if filter_.severity is not None:
        conditions.append(f"severity = ${param_index}")
        args.append(filter_.severity)
        param_index += 1

    return param_index


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
