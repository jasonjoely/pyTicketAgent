"""Load and validate ``embedding_providers.json`` into app config + registry."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pyticketagent_core.embeddings.embedding_app_config import EmbeddingAppConfig
from pyticketagent_core.embeddings.embedding_model_binding import EmbeddingModelBinding
from pyticketagent_core.embeddings.embedding_model_definition import (
    EmbeddingModelDefinition,
)
from pyticketagent_core.embeddings.embedding_provider_definition import (
    EmbeddingProviderDefinition,
)
from pyticketagent_core.embeddings.embedding_provider_kind import EmbeddingProviderKind
from pyticketagent_core.embeddings.embedding_providers_file import EmbeddingProvidersFile
from pyticketagent_core.embeddings.embedding_providers_reader import (
    read_embedding_providers_json,
)
from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.embedding_space_binding_config import (
    EmbeddingSpaceBindingConfig,
)
from pyticketagent_core.embeddings.json_embedding_provider_registry import (
    JsonEmbeddingProviderRegistry,
)

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_API_ENDPOINT = "http://localhost:11434/api"


class JsonEmbeddingProviderRegistryLoader:
    """Parse embedding providers JSON (catalog + active spaces) into app config."""

    def load_default(self) -> EmbeddingAppConfig:
        """Load the packaged ``embedding_providers.json`` catalog."""
        return self.load_json(
            read_embedding_providers_json(), source="embedding_providers.json"
        )

    def load(self, file_path: str | Path) -> EmbeddingAppConfig:
        path = Path(file_path)
        if not path.is_file():
            logger.error("Embedding providers file not found: %s", path)
            raise FileNotFoundError(f"Embedding providers file not found: {path}")
        return self.load_json(path.read_text(encoding="utf-8"), source=str(path))

    def load_json(self, json_text: str, *, source: str) -> EmbeddingAppConfig:
        try:
            raw = json.loads(json_text)
            file_model = EmbeddingProvidersFile.model_validate(raw)
        except (json.JSONDecodeError, ValueError) as ex:
            logger.error("Invalid embedding providers JSON in %s", source)
            raise ValueError(
                f"Invalid embedding providers JSON in: {source}"
            ) from ex

        if not file_model.providers:
            raise ValueError(
                f"No embedding provider definitions found in: {source}"
            )

        providers = self._validate_and_normalize(file_model.providers, source)
        all_models = self._build_selectable_models(providers)
        if not all_models:
            raise ValueError(
                "No selectable embedding models remain after loading providers."
            )

        registry = JsonEmbeddingProviderRegistry(providers, all_models)
        fastembed = self._require_space(
            file_model.spaces, EmbeddingSpace.FASTEMBED, source
        )
        ollama = self._require_space(
            file_model.spaces, EmbeddingSpace.OLLAMA, source
        )
        self._validate_space_binding(registry, EmbeddingSpace.FASTEMBED, fastembed, source)
        self._validate_space_binding(registry, EmbeddingSpace.OLLAMA, ollama, source)

        default_search_space = self._parse_search_space(
            file_model.default_search_space, source
        )

        logger.info(
            "Loaded %s embedding provider(s) with %s model(s) from %s "
            "(fastembed=%s enabled=%s; ollama=%s enabled=%s)",
            len(providers),
            len(all_models),
            source,
            f"{fastembed.provider_id}:{fastembed.model}",
            fastembed.enabled,
            f"{ollama.provider_id}:{ollama.model}",
            ollama.enabled,
        )
        return EmbeddingAppConfig(
            registry=registry,
            request_timeout_seconds=file_model.request_timeout_seconds,
            default_search_space=default_search_space,
            fastembed=fastembed,
            ollama=ollama,
        )

    @staticmethod
    def _require_space(
        spaces: dict[str, EmbeddingSpaceBindingConfig],
        space: EmbeddingSpace,
        source: str,
    ) -> EmbeddingSpaceBindingConfig:
        binding = spaces.get(space.value)
        if binding is None:
            raise ValueError(
                f"Embedding config in {source} is missing spaces.{space.value}."
            )
        return EmbeddingSpaceBindingConfig(
            enabled=binding.enabled,
            provider_id=binding.provider_id.strip(),
            model=binding.model.strip(),
        )

    @staticmethod
    def _validate_space_binding(
        registry: JsonEmbeddingProviderRegistry,
        space: EmbeddingSpace,
        binding: EmbeddingSpaceBindingConfig,
        source: str,
    ) -> None:
        if not binding.provider_id:
            raise ValueError(
                f"spaces.{space.value}.providerId in {source} must be non-empty."
            )
        if not binding.model:
            raise ValueError(
                f"spaces.{space.value}.model in {source} must be non-empty."
            )
        try:
            registry.resolve_binding(binding.provider_id, binding.model)
        except KeyError as ex:
            raise ValueError(
                f"spaces.{space.value} in {source} refers to unknown "
                f"provider/model '{binding.provider_id}/{binding.model}'."
            ) from ex

    @staticmethod
    def _parse_search_space(value: str, source: str) -> EmbeddingSpace:
        trimmed = value.strip()
        try:
            return EmbeddingSpace(trimmed)
        except ValueError as ex:
            allowed = ", ".join(s.value for s in EmbeddingSpace)
            raise ValueError(
                f"defaultSearchSpace '{value}' in {source} is invalid. "
                f"Allowed: {allowed}."
            ) from ex

    def _validate_and_normalize(
        self,
        raw_providers: list[EmbeddingProviderDefinition],
        source: str,
    ) -> list[EmbeddingProviderDefinition]:
        providers: list[EmbeddingProviderDefinition] = []
        seen_ids: set[str] = set()

        for index, provider in enumerate(raw_providers):
            if not provider.id.strip():
                raise ValueError(
                    f"Embedding provider at index {index} in {source} "
                    "is missing a non-empty id."
                )

            provider_id = provider.id.strip()
            if provider_id.casefold() in seen_ids:
                raise ValueError(
                    f"Duplicate embedding provider id '{provider_id}' in {source}."
                )
            seen_ids.add(provider_id.casefold())

            api_endpoint = self._normalize_api_endpoint(provider)

            if not provider.models:
                raise ValueError(
                    f"Embedding provider '{provider_id}' in {source} "
                    "must define at least one model."
                )

            seen_models: set[str] = set()
            normalized_models: list[EmbeddingModelDefinition] = []
            for model in provider.models:
                name = model.model.strip()
                if not name:
                    raise ValueError(
                        f"Embedding provider '{provider_id}' in {source} "
                        "contains an empty model name."
                    )
                if name.casefold() in seen_models:
                    raise ValueError(
                        f"Duplicate model '{name}' for provider '{provider_id}'."
                    )
                seen_models.add(name.casefold())
                normalized_models.append(
                    EmbeddingModelDefinition(
                        model=name, dimensions=model.dimensions
                    )
                )

            if (
                provider.kind == EmbeddingProviderKind.OLLAMA
                and not api_endpoint
            ):
                raise ValueError(
                    f"Embedding provider '{provider_id}' in {source} "
                    "requires apiEndpoint."
                )

            providers.append(
                EmbeddingProviderDefinition(
                    id=provider_id,
                    kind=provider.kind,
                    api_endpoint=api_endpoint,
                    models=normalized_models,
                )
            )

        return providers

    @staticmethod
    def _normalize_api_endpoint(
        provider: EmbeddingProviderDefinition,
    ) -> str | None:
        if provider.kind == EmbeddingProviderKind.OLLAMA:
            if not provider.api_endpoint or not provider.api_endpoint.strip():
                return _DEFAULT_OLLAMA_API_ENDPOINT
            return provider.api_endpoint.strip()
        if not provider.api_endpoint or not provider.api_endpoint.strip():
            return None
        return provider.api_endpoint.strip()

    def _build_selectable_models(
        self,
        providers: list[EmbeddingProviderDefinition],
    ) -> list[EmbeddingModelBinding]:
        all_models: list[EmbeddingModelBinding] = []
        seen: set[str] = set()

        for provider in providers:
            for model in provider.models:
                key = f"{provider.id.casefold()}\0{model.model.casefold()}"
                if key in seen:
                    continue
                seen.add(key)
                all_models.append(
                    EmbeddingModelBinding(
                        provider_id=provider.id,
                        model=model.model,
                        dimensions=model.dimensions,
                    )
                )

        return all_models
