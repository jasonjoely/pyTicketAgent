"""Both embedding spaces for a ticket upsert."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.embeddings.embedding_space_write import EmbeddingSpaceWrite


@dataclass(frozen=True, slots=True)
class TicketEmbeddingsWrite:
    """FastEmbed and Ollama write instructions for one upsert."""

    fastembed: EmbeddingSpaceWrite
    ollama: EmbeddingSpaceWrite
