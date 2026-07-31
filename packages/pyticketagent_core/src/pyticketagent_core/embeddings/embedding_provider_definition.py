"""Embedding provider definition from the providers catalog."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.embeddings.embedding_model_definition import (
    EmbeddingModelDefinition,
)
from pyticketagent_core.embeddings.embedding_provider_kind import EmbeddingProviderKind


class EmbeddingProviderDefinition(BaseModel):
    """One provider entry from ``embedding_providers.json``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    kind: EmbeddingProviderKind
    api_endpoint: str | None = Field(default=None, alias="apiEndpoint")
    models: list[EmbeddingModelDefinition] = Field(default_factory=list)
