"""Build the POC dual-space embedding runtime from embedding app config."""

from __future__ import annotations

import logging

from pyticketagent_core.embeddings.dual_space_embedding_runtime import (
    DualSpaceEmbeddingRuntime,
)
from pyticketagent_core.embeddings.embedding_app_config import EmbeddingAppConfig
from pyticketagent_core.embeddings.embedding_client_factory import EmbeddingClientFactory
from pyticketagent_core.embeddings.embedding_space_binding_config import (
    EmbeddingSpaceBindingConfig,
)

logger = logging.getLogger(__name__)


class DualSpaceEmbeddingRuntimeFactory:
    """Resolve FastEmbed + Ollama POC bindings and create clients."""

    def __init__(
        self,
        app_config: EmbeddingAppConfig,
        client_factory: EmbeddingClientFactory | None = None,
    ) -> None:
        self._app_config = app_config
        self._client_factory = client_factory or EmbeddingClientFactory(
            request_timeout_seconds=float(app_config.request_timeout_seconds)
        )

    def create(self) -> DualSpaceEmbeddingRuntime:
        registry = self._app_config.registry
        fastembed_binding = self._resolve(self._app_config.fastembed)
        ollama_binding = self._resolve(self._app_config.ollama)

        fastembed_provider = registry.get_provider(
            self._app_config.fastembed.provider_id
        )
        ollama_provider = registry.get_provider(self._app_config.ollama.provider_id)

        try:
            fastembed_client = self._client_factory.create_client(
                fastembed_binding, fastembed_provider
            )
        except Exception:
            logger.error(
                "Failed to create FastEmbed embedding client for model %s",
                fastembed_binding.display_name,
                exc_info=True,
            )
            raise

        try:
            ollama_client = self._client_factory.create_client(
                ollama_binding, ollama_provider
            )
        except Exception:
            logger.error(
                "Failed to create Ollama embedding client for model %s",
                ollama_binding.display_name,
                exc_info=True,
            )
            raise

        logger.info(
            "Dual embedding runtime ready: fastembed=%s enabled=%s; "
            "ollama=%s enabled=%s",
            fastembed_binding.display_name,
            self._app_config.fastembed.enabled,
            ollama_binding.display_name,
            self._app_config.ollama.enabled,
        )
        return DualSpaceEmbeddingRuntime(
            fastembed_client=fastembed_client,
            fastembed_binding=fastembed_binding,
            fastembed_enabled=self._app_config.fastembed.enabled,
            ollama_client=ollama_client,
            ollama_binding=ollama_binding,
            ollama_enabled=self._app_config.ollama.enabled,
            default_search_space=self._app_config.default_search_space,
        )

    def _resolve(self, binding: EmbeddingSpaceBindingConfig):
        return self._app_config.registry.resolve_binding(
            binding.provider_id, binding.model
        )
