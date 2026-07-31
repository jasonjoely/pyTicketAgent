"""Factory that builds provider-specific embedding clients."""

from __future__ import annotations

from pyticketagent_core.embeddings.embedding_client import EmbeddingClient
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_provider_definition import (
    EmbeddingProviderDefinition,
)
from pyticketagent_core.embeddings.embedding_provider_kind import EmbeddingProviderKind
from pyticketagent_core.embeddings.fastembed_embedding_client import (
    FastEmbedEmbeddingClient,
)
from pyticketagent_core.embeddings.ollama_embedding_client import OllamaEmbeddingClient


class EmbeddingClientFactory:
    """Create an ``EmbeddingClient`` for a resolved provider/model binding."""

    def __init__(self, *, request_timeout_seconds: float) -> None:
        self._request_timeout_seconds = request_timeout_seconds

    def create_client(
        self,
        binding: EmbeddingModelBinding,
        provider: EmbeddingProviderDefinition,
    ) -> EmbeddingClient:
        if provider.kind == EmbeddingProviderKind.FASTEMBED:
            return FastEmbedEmbeddingClient(
                binding.model,
                expected_dimensions=binding.dimensions,
            )

        if provider.kind == EmbeddingProviderKind.OLLAMA:
            if not provider.api_endpoint:
                raise ValueError(
                    f"Provider '{provider.id}' requires apiEndpoint "
                    "but none is configured."
                )
            return OllamaEmbeddingClient(
                provider.api_endpoint,
                binding.model,
                expected_dimensions=binding.dimensions,
                timeout_seconds=self._request_timeout_seconds,
            )

        raise ValueError(f"Unsupported embedding provider kind: {provider.kind}")
