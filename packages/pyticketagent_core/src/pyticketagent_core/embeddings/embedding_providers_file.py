"""Root schema for ``embedding_providers.json`` (catalog + active config)."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.embeddings.embedding_provider_definition import (
    EmbeddingProviderDefinition,
)
from pyticketagent_core.embeddings.embedding_space_binding_config import (
    EmbeddingSpaceBindingConfig,
)


class EmbeddingProvidersFile(BaseModel):
    """Packaged embedding API configuration document."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    request_timeout_seconds: int = Field(
        default=120, alias="requestTimeoutSeconds", gt=0
    )
    default_search_space: str = Field(
        default="ollama", alias="defaultSearchSpace"
    )
    spaces: dict[str, EmbeddingSpaceBindingConfig]
    providers: list[EmbeddingProviderDefinition]
