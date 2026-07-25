"""Resolve the active LLM provider/model from settings / environment."""

from __future__ import annotations

import logging
import os

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind
from pyticketagent_core.ai.json_ai_provider_registry import JsonAiProviderRegistry
from pyticketagent_core.configuration.settings import Settings

logger = logging.getLogger(__name__)


class EnvVarAiModelBindingResolver:
    """Resolve ``AiModelBinding`` from ``PYTICKETAGENT_LLM_*`` settings."""

    def __init__(
        self,
        registry: JsonAiProviderRegistry,
        settings: Settings,
    ) -> None:
        self._registry = registry
        self._settings = settings

    def resolve_binding(self) -> AiModelBinding:
        provider_id = (self._settings.llm_provider or "").strip()
        if not provider_id:
            logger.error(
                "Environment variable PYTICKETAGENT_LLM_PROVIDER is not set. "
                "Configure it to an AI provider id from ai_providers.json."
            )
            raise ValueError(
                "Environment variable 'PYTICKETAGENT_LLM_PROVIDER' is not set."
            )

        model_name = (self._settings.llm_model or "").strip()
        if not model_name:
            logger.error(
                "Environment variable PYTICKETAGENT_LLM_MODEL is not set. "
                "Configure it to a model name for provider '%s'.",
                provider_id,
            )
            raise ValueError(
                "Environment variable 'PYTICKETAGENT_LLM_MODEL' is not set."
            )

        try:
            provider = self._registry.get_provider(provider_id)
        except KeyError:
            logger.error(
                "AI provider '%s' from PYTICKETAGENT_LLM_PROVIDER was not found "
                "in ai_providers.json.",
                provider_id,
            )
            raise ValueError(
                f"AI provider '{provider_id}' was not found in ai_providers.json."
            ) from None

        canonical_model = next(
            (
                m.model
                for m in provider.models
                if m.model.casefold() == model_name.casefold()
            ),
            None,
        )
        if canonical_model is None:
            logger.error(
                "Model '%s' from PYTICKETAGENT_LLM_MODEL is not configured for "
                "provider '%s'.",
                model_name,
                provider_id,
            )
            raise ValueError(
                f"Model '{model_name}' is not configured for provider '{provider.id}'."
            )

        if self._requires_api_key(provider.kind) and not self._has_api_key(provider):
            logger.error(
                "Provider '%s' requires environment variable %s, but it is not set.",
                provider.id,
                provider.api_key,
            )
            raise ValueError(
                f"Environment variable '{provider.api_key}' is not set for "
                f"provider '{provider.id}'."
            )

        return AiModelBinding(provider_id=provider.id, model=canonical_model)

    @staticmethod
    def _requires_api_key(kind: AiProviderKind) -> bool:
        return kind in (AiProviderKind.OPEN_AI_COMPATIBLE, AiProviderKind.GEMINI)

    @staticmethod
    def _has_api_key(provider: AiProviderDefinition) -> bool:
        if not provider.api_key:
            return False
        value = os.environ.get(provider.api_key)
        return bool(value and value.strip())
