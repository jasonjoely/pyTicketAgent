"""Protocol for looking up AI providers by id."""

from __future__ import annotations

from typing import Protocol

from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition


class AiProviderRegistry(Protocol):
    """Lookup AI providers from a loaded catalog."""

    def get_provider(self, provider_id: str) -> AiProviderDefinition:
        """Return the provider with the given id, or raise KeyError."""
        ...
