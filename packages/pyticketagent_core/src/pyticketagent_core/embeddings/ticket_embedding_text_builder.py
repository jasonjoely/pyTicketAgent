"""Build document/query strings for ticket embeddings."""

from __future__ import annotations

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

_NOMIC_DOCUMENT_PREFIX = "search_document: "
_NOMIC_QUERY_PREFIX = "search_query: "


class TicketEmbeddingTextBuilder:
    """Compose embeddable text for a ticket (and optional query prefixes)."""

    def build_document(self, ticket: IncidentTicket, space: EmbeddingSpace) -> str:
        body = self._build_body(ticket)
        if space == EmbeddingSpace.OLLAMA:
            return f"{_NOMIC_DOCUMENT_PREFIX}{body}"
        return body

    def build_query(self, query: str, space: EmbeddingSpace) -> str:
        trimmed = query.strip()
        if space == EmbeddingSpace.OLLAMA:
            return f"{_NOMIC_QUERY_PREFIX}{trimmed}"
        return trimmed

    @staticmethod
    def _build_body(ticket: IncidentTicket) -> str:
        tags = ", ".join(ticket.tags) if ticket.tags else ""
        parts = [
            f"Service: {ticket.service}",
            f"Environment: {ticket.environment}",
            f"Tags: {tags}",
            f"Title: {ticket.title}",
            "",
            ticket.description,
        ]
        resolution = (ticket.resolution_summary or "").strip()
        if resolution:
            parts.extend(["", f"Resolution: {resolution}"])
        return "\n".join(parts)
