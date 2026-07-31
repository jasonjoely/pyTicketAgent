"""In-memory registry of embedding providers loaded from JSON."""

from __future__ import annotations

from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_provider_definition import (
    EmbeddingProviderDefinition,
)


class JsonEmbeddingProviderRegistry:
    """Lookup providers and selectable models from a loaded catalog."""

    def __init__(
        self,
        providers: list[EmbeddingProviderDefinition],
        all_models: list[EmbeddingModelBinding],
    ) -> None:
        self.providers = providers
        self.all_models = all_models
        self._providers = {p.id.casefold(): p for p in providers}

    def get_provider(self, provider_id: str) -> EmbeddingProviderDefinition:
        provider = self._providers.get(provider_id.casefold())
        if provider is None:
            raise KeyError(
                f"Embedding provider '{provider_id}' was not found in the registry."
            )
        return provider

    def resolve_binding(
        self, provider_id: str, model: str
    ) -> EmbeddingModelBinding:
        provider = self.get_provider(provider_id)
        for entry in provider.models:
            if entry.model.casefold() == model.casefold():
                return EmbeddingModelBinding(
                    provider_id=provider.id,
                    model=entry.model,
                    dimensions=entry.dimensions,
                )
        raise KeyError(
            f"Embedding model '{model}' was not found for provider '{provider.id}'."
        )
