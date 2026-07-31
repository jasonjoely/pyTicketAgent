"""Resolved dual-space embedding clients and model bindings for ingest."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.embeddings.embedding_client import EmbeddingClient
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace


@dataclass(frozen=True, slots=True)
class DualSpaceEmbeddingRuntime:
    """FastEmbed + Ollama clients wired for the POC dual columns."""

    fastembed_client: EmbeddingClient
    fastembed_binding: EmbeddingModelBinding
    fastembed_enabled: bool
    ollama_client: EmbeddingClient
    ollama_binding: EmbeddingModelBinding
    ollama_enabled: bool
    default_search_space: EmbeddingSpace
