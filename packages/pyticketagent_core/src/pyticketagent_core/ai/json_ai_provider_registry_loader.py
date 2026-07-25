"""Load and validate ``ai_providers.json`` into a registry."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from pyticketagent_core.ai.ai_model_binding import AiModelBinding
from pyticketagent_core.ai.ai_model_definition import AiModelDefinition
from pyticketagent_core.ai.ai_provider_definition import AiProviderDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind
from pyticketagent_core.ai.ai_providers_resource import read_ai_providers_json
from pyticketagent_core.ai.json_ai_provider_registry import JsonAiProviderRegistry

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_API_ENDPOINT = "http://localhost:11434/api"


class JsonAiProviderRegistryLoader:
    """Parse provider catalog JSON and build a registry."""

    def load_default(self) -> JsonAiProviderRegistry:
        """Load the packaged ``ai_providers.json`` catalog."""
        return self.load_json(read_ai_providers_json(), source="ai_providers.json")

    def load(self, file_path: str | Path) -> JsonAiProviderRegistry:
        path = Path(file_path)
        if not path.is_file():
            logger.error("AI providers file not found: %s", path)
            raise FileNotFoundError(f"AI providers file not found: {path}")
        return self.load_json(path.read_text(encoding="utf-8"), source=str(path))

    def load_json(self, json_text: str, *, source: str) -> JsonAiProviderRegistry:
        try:
            raw = json.loads(json_text)
            raw_providers = [AiProviderDefinition.model_validate(item) for item in raw]
        except (json.JSONDecodeError, ValueError) as ex:
            logger.error("Invalid AI providers JSON in %s", source)
            raise ValueError(f"Invalid AI providers JSON in: {source}") from ex

        if not raw_providers:
            raise ValueError(f"No AI provider definitions found in: {source}")

        providers = self._validate_and_normalize(raw_providers, source)
        all_models = self._build_selectable_models(providers)

        if not all_models:
            raise ValueError(
                "No selectable AI models remain after loading providers. "
                "Configure at least one provider with valid credentials and models."
            )

        logger.info(
            "Loaded %s AI provider(s) with %s selectable model(s) from %s",
            len(providers),
            len(all_models),
            source,
        )
        return JsonAiProviderRegistry(providers, all_models)

    def _validate_and_normalize(
        self,
        raw_providers: list[AiProviderDefinition],
        source: str,
    ) -> list[AiProviderDefinition]:
        providers: list[AiProviderDefinition] = []
        seen_ids: set[str] = set()

        for index, provider in enumerate(raw_providers):
            if not provider.id.strip():
                raise ValueError(
                    f"AI provider at index {index} in {source} is missing a non-empty id."
                )

            provider_id = provider.id.strip()
            if provider_id.casefold() in seen_ids:
                raise ValueError(f"Duplicate AI provider id '{provider_id}' in {source}.")
            seen_ids.add(provider_id.casefold())

            api_endpoint = self._normalize_api_endpoint(provider)
            self._validate_provider_requirements(provider, api_endpoint, source)

            if not provider.models:
                raise ValueError(
                    f"AI provider '{provider_id}' in {source} must define at least one model."
                )

            seen_models: set[str] = set()
            normalized_models: list[AiModelDefinition] = []
            for model in provider.models:
                name = model.model.strip()
                if not name:
                    raise ValueError(
                        f"AI provider '{provider_id}' in {source} contains an empty model name."
                    )
                if name.casefold() in seen_models:
                    raise ValueError(
                        f"Duplicate model '{name}' for provider '{provider_id}'."
                    )
                seen_models.add(name.casefold())
                normalized_models.append(AiModelDefinition(model=name))

            providers.append(
                AiProviderDefinition(
                    id=provider_id,
                    kind=provider.kind,
                    api_endpoint=api_endpoint,
                    api_key=(
                        provider.api_key.strip()
                        if provider.api_key and provider.api_key.strip()
                        else None
                    ),
                    models=normalized_models,
                )
            )

        return providers

    @staticmethod
    def _normalize_api_endpoint(provider: AiProviderDefinition) -> str | None:
        if provider.kind == AiProviderKind.OLLAMA:
            if not provider.api_endpoint or not provider.api_endpoint.strip():
                return _DEFAULT_OLLAMA_API_ENDPOINT
            return provider.api_endpoint.strip()
        if not provider.api_endpoint or not provider.api_endpoint.strip():
            return None
        return provider.api_endpoint.strip()

    @staticmethod
    def _validate_provider_requirements(
        provider: AiProviderDefinition,
        api_endpoint: str | None,
        source: str,
    ) -> None:
        if provider.kind == AiProviderKind.OPEN_AI_COMPATIBLE:
            if not api_endpoint:
                raise ValueError(
                    f"AI provider '{provider.id}' in {source} requires apiEndpoint."
                )
            if not provider.api_key or not provider.api_key.strip():
                raise ValueError(
                    f"AI provider '{provider.id}' in {source} requires apiKey "
                    "(environment variable name)."
                )
        elif provider.kind == AiProviderKind.GEMINI:
            if not provider.api_key or not provider.api_key.strip():
                raise ValueError(
                    f"AI provider '{provider.id}' in {source} requires apiKey "
                    "(environment variable name)."
                )

    def _build_selectable_models(
        self,
        providers: list[AiProviderDefinition],
    ) -> list[AiModelBinding]:
        all_models: list[AiModelBinding] = []
        seen: set[str] = set()

        for provider in providers:
            if self._requires_api_key(provider.kind) and not self._has_api_key(provider):
                logger.warning(
                    "Skipping provider %s: environment variable %s is not set",
                    provider.id,
                    provider.api_key,
                )
                continue

            for model in provider.models:
                key = f"{provider.id.casefold()}\0{model.model.casefold()}"
                if key in seen:
                    continue
                seen.add(key)
                all_models.append(
                    AiModelBinding(provider_id=provider.id, model=model.model)
                )

        return all_models

    @staticmethod
    def _requires_api_key(kind: AiProviderKind) -> bool:
        return kind in (AiProviderKind.OPEN_AI_COMPATIBLE, AiProviderKind.GEMINI)

    @staticmethod
    def _has_api_key(provider: AiProviderDefinition) -> bool:
        if not provider.api_key:
            return False
        value = os.environ.get(provider.api_key)
        return bool(value and value.strip())
