"""Protocol for building provider-specific chat clients."""

from __future__ import annotations

from typing import Protocol

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.chat_client import ChatClient


class ChatClientFactory(Protocol):
    """Create a ``ChatClient`` for a resolved provider/model binding."""

    def create_client(
        self,
        binding: AiModelBinding,
        provider: AiProviderDefinition,
    ) -> ChatClient:
        """Return a chat client configured for the given provider/model."""
        ...
