"""In-memory registry of AI providers loaded from JSON."""

from __future__ import annotations

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition


class JsonAiProviderRegistry:
    """Lookup providers and selectable models from a loaded catalog."""

    def __init__(
        self,
        providers: list[AiProviderDefinition],
        all_models: list[AiModelBinding],
    ) -> None:
        self.providers = providers
        self.all_models = all_models
        self._providers = {p.id.casefold(): p for p in providers}

    def get_provider(self, provider_id: str) -> AiProviderDefinition:
        provider = self._providers.get(provider_id.casefold())
        if provider is None:
            raise KeyError(f"AI provider '{provider_id}' was not found in the registry.")
        return provider
