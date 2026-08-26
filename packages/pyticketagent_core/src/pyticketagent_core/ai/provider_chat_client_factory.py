"""Factory that builds provider-specific chat clients."""

from __future__ import annotations

import os

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind
from pyticketagent_core.ai.chat_client import ChatClient
from pyticketagent_core.ai.gemini_chat_client import GeminiChatClient
from pyticketagent_core.ai.groq_chat_client import GroqChatClient
from pyticketagent_core.ai.llm_transient_retry_options import LlmTransientRetryOptions
from pyticketagent_core.ai.ollama_chat_client import OllamaChatClient
from pyticketagent_core.ai.retrying_chat_client import RetryingChatClient
from pyticketagent_core.configuration.settings import Settings


class ProviderChatClientFactory:
    """Create a ``ChatClient`` for a resolved provider/model binding."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_client(
        self,
        binding: AiModelBinding,
        provider: AiProviderDefinition,
    ) -> ChatClient:
        timeout = float(self._settings.llm_request_timeout_seconds)
        retry_options = LlmTransientRetryOptions.from_settings(self._settings)

        if provider.kind == AiProviderKind.OLLAMA:
            if not provider.api_endpoint:
                raise ValueError(
                    f"Provider '{provider.id}' requires apiEndpoint but none is configured."
                )
            inner: ChatClient = OllamaChatClient(
                provider.api_endpoint,
                binding.model,
                timeout_seconds=timeout,
            )
        elif provider.kind == AiProviderKind.OPEN_AI_COMPATIBLE:
            inner = GroqChatClient(
                self._resolve_api_key(provider),
                binding.model,
                timeout_seconds=timeout,
                base_url=provider.api_endpoint,
            )
        elif provider.kind == AiProviderKind.GEMINI:
            inner = GeminiChatClient(
                self._resolve_api_key(provider),
                binding.model,
                timeout_seconds=timeout,
            )
        else:
            raise ValueError(f"Unsupported AI provider kind: {provider.kind}")

        return RetryingChatClient(inner, retry_options)

    @staticmethod
    def _resolve_api_key(provider: AiProviderDefinition) -> str:
        if not provider.api_key:
            raise ValueError(
                f"Provider '{provider.id}' requires apiKey (environment variable name) "
                "but none is configured."
            )
        value = os.environ.get(provider.api_key)
        if not value or not value.strip():
            raise ValueError(
                f"Environment variable '{provider.api_key}' is not set for "
                f"provider '{provider.id}'."
            )
        return value.strip()
