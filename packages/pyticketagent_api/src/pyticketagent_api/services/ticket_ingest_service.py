"""Ingest service: validate tickets, dual-embed, upsert with soft-fail semantics."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from pyticketagent_core.data.database_transient_error_retry import execute_with_retry
from pyticketagent_core.data.ticket_repository import TicketRepository
from pyticketagent_core.data.upsert_outcome import UpsertOutcome
from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)
from pyticketagent_core.embeddings.embedding_client import EmbeddingClient
from pyticketagent_core.embeddings.embedding_content_hasher import EmbeddingContentHasher
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.embedding_space_write import EmbeddingSpaceWrite
from pyticketagent_core.embeddings.ticket_embedding_meta import TicketEmbeddingMeta
from pyticketagent_core.embeddings.ticket_embedding_space_meta import (
    TicketEmbeddingSpaceMeta,
)
from pyticketagent_core.embeddings.ticket_embedding_text_builder import (
    TicketEmbeddingTextBuilder,
)
from pyticketagent_core.embeddings.ticket_embeddings_write import TicketEmbeddingsWrite
from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_core.tickets.ticket_state import TicketState

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
        embedding_runtime: DualSpaceEmbeddingRuntime | None = None,
        text_builder: TicketEmbeddingTextBuilder | None = None,
        content_hasher: EmbeddingContentHasher | None = None,
        retry_max_attempts: int = 3,
        retry_initial_delay_ms: int = 200,
        retry_max_delay_ms: int = 2000,
    ) -> None:
        self._ticket_repository = ticket_repository
        self._embedding_runtime = embedding_runtime
        self._text_builder = text_builder or TicketEmbeddingTextBuilder()
        self._content_hasher = content_hasher or EmbeddingContentHasher()
        self._retry_max_attempts = retry_max_attempts
        self._retry_initial_delay_ms = retry_initial_delay_ms
        self._retry_max_delay_ms = retry_max_delay_ms

    async def ingest(self, tickets: list[IncidentTicketRequest]) -> IngestResponse:
        counts = IngestCounts()
        skipped: list[SkippedTicketItem] = []
        embed_stats = _EmbeddingBatchStats()

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
                embeddings = await self._prepare_embeddings(ticket, embed_stats)
                outcome = await execute_with_retry(
                    lambda t=ticket, e=embeddings: self._ticket_repository.upsert(
                        t, e
                    ),
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

        logger.info(
            "Ingest embedding summary: "
            "fastembed ok=%s failed=%s skipped=%s; "
            "ollama ok=%s failed=%s skipped=%s; "
            "tickets created=%s updated=%s skipped=%s",
            embed_stats.fastembed_ok,
            embed_stats.fastembed_failed,
            embed_stats.fastembed_skipped,
            embed_stats.ollama_ok,
            embed_stats.ollama_failed,
            embed_stats.ollama_skipped,
            counts.ingested,
            counts.updated,
            counts.skipped,
        )
        return IngestResponse(counts=counts, skipped=skipped)

    async def _prepare_embeddings(
        self,
        ticket: IncidentTicket,
        stats: _EmbeddingBatchStats,
    ) -> TicketEmbeddingsWrite:
        if self._embedding_runtime is None:
            stats.fastembed_skipped += 1
            stats.ollama_skipped += 1
            return TicketEmbeddingsWrite(
                fastembed=EmbeddingSpaceWrite.preserve(),
                ollama=EmbeddingSpaceWrite.preserve(),
            )

        existing = await self._ticket_repository.get_embedding_meta(ticket.id)
        runtime = self._embedding_runtime

        fastembed_text = self._text_builder.build_document(
            ticket, EmbeddingSpace.FASTEMBED
        )
        ollama_text = self._text_builder.build_document(
            ticket, EmbeddingSpace.OLLAMA
        )
        fastembed_hash = self._content_hasher.hash_text(fastembed_text)
        ollama_hash = self._content_hasher.hash_text(ollama_text)

        fastembed_task = self._resolve_space_write(
            ticket_id=ticket.id,
            space=EmbeddingSpace.FASTEMBED,
            enabled=runtime.fastembed_enabled,
            client=runtime.fastembed_client,
            binding=runtime.fastembed_binding,
            text=fastembed_text,
            content_hash=fastembed_hash,
            existing=existing.fastembed if existing else None,
            stats=stats,
        )
        ollama_task = self._resolve_space_write(
            ticket_id=ticket.id,
            space=EmbeddingSpace.OLLAMA,
            enabled=runtime.ollama_enabled,
            client=runtime.ollama_client,
            binding=runtime.ollama_binding,
            text=ollama_text,
            content_hash=ollama_hash,
            existing=existing.ollama if existing else None,
            stats=stats,
        )
        fastembed_write, ollama_write = await asyncio.gather(
            fastembed_task, ollama_task
        )

        if (
            fastembed_write.update
            and fastembed_write.vector is None
            and ollama_write.update
            and ollama_write.vector is None
        ):
            logger.warning(
                "ticket_id=%s both embedding spaces failed; "
                "upsert continues with both embeddings NULL",
                ticket.id,
            )

        return TicketEmbeddingsWrite(
            fastembed=fastembed_write,
            ollama=ollama_write,
        )

    async def _resolve_space_write(
        self,
        *,
        ticket_id: int,
        space: EmbeddingSpace,
        enabled: bool,
        client: EmbeddingClient,
        binding: EmbeddingModelBinding,
        text: str,
        content_hash: str,
        existing: TicketEmbeddingSpaceMeta | None,
        stats: _EmbeddingBatchStats,
    ) -> EmbeddingSpaceWrite:
        model_id = binding.display_name

        if not enabled:
            _bump_skipped(stats, space)
            logger.debug(
                "ticket_id=%s space=%s model=%s reason=disabled",
                ticket_id,
                space.value,
                model_id,
            )
            return EmbeddingSpaceWrite.preserve()

        if (
            existing is not None
            and existing.has_vector
            and existing.content_hash == content_hash
            and existing.model == model_id
        ):
            _bump_skipped(stats, space)
            logger.debug(
                "ticket_id=%s space=%s model=%s reason=unchanged",
                ticket_id,
                space.value,
                model_id,
            )
            return EmbeddingSpaceWrite.preserve()

        logger.debug(
            "ticket_id=%s space=%s model=%s text_chars=%s",
            ticket_id,
            space.value,
            model_id,
            len(text),
        )
        started = time.perf_counter()
        try:
            vectors = await client.embed([text])
            duration_ms = int((time.perf_counter() - started) * 1000)
            if not vectors:
                raise ValueError("Embedding client returned no vectors.")
            vector = vectors[0]
            if len(vector) != binding.dimensions:
                logger.warning(
                    "ticket_id=%s space=%s model=%s expected_dim=%s actual_dim=%s",
                    ticket_id,
                    space.value,
                    model_id,
                    binding.dimensions,
                    len(vector),
                )
                _bump_failed(stats, space)
                return EmbeddingSpaceWrite.clear()

            logger.debug(
                "ticket_id=%s space=%s model=%s dimensions=%s duration_ms=%s",
                ticket_id,
                space.value,
                model_id,
                len(vector),
                duration_ms,
            )
            _bump_ok(stats, space)
            return EmbeddingSpaceWrite.set_vector(
                vector,
                model=model_id,
                content_hash=content_hash,
                updated_at=datetime.now(timezone.utc),
            )
        except Exception as ex:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "ticket_id=%s space=%s model=%s error=%s duration_ms=%s; "
                "setting embedding NULL",
                ticket_id,
                space.value,
                model_id,
                ex,
                duration_ms,
                exc_info=True,
            )
            _bump_failed(stats, space)
            return EmbeddingSpaceWrite.clear()


class _EmbeddingBatchStats:
    def __init__(self) -> None:
        self.fastembed_ok = 0
        self.fastembed_failed = 0
        self.fastembed_skipped = 0
        self.ollama_ok = 0
        self.ollama_failed = 0
        self.ollama_skipped = 0


def _bump_ok(stats: _EmbeddingBatchStats, space: EmbeddingSpace) -> None:
    if space == EmbeddingSpace.FASTEMBED:
        stats.fastembed_ok += 1
    else:
        stats.ollama_ok += 1


def _bump_failed(stats: _EmbeddingBatchStats, space: EmbeddingSpace) -> None:
    if space == EmbeddingSpace.FASTEMBED:
        stats.fastembed_failed += 1
    else:
        stats.ollama_failed += 1


def _bump_skipped(stats: _EmbeddingBatchStats, space: EmbeddingSpace) -> None:
    if space == EmbeddingSpace.FASTEMBED:
        stats.fastembed_skipped += 1
    else:
        stats.ollama_skipped += 1


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
        status=request.status or TicketState.UNASSIGNED,
    )
    return ticket, ""
