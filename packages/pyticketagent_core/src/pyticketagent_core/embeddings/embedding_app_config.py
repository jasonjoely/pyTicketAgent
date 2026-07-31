"""Loaded embedding catalog + active dual-space configuration."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.embedding_space_binding_config import (
    EmbeddingSpaceBindingConfig,
)
from pyticketagent_core.embeddings.json_embedding_provider_registry import (
    JsonEmbeddingProviderRegistry,
)


@dataclass(frozen=True, slots=True)
class EmbeddingAppConfig:
    """Runtime embedding configuration from ``embedding_providers.json``."""

    registry: JsonEmbeddingProviderRegistry
    request_timeout_seconds: int
    default_search_space: EmbeddingSpace
    fastembed: EmbeddingSpaceBindingConfig
    ollama: EmbeddingSpaceBindingConfig
