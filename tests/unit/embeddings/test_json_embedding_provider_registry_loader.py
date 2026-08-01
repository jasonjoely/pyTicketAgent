"""Tests for embedding provider catalog + active config loading."""

import pytest

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.embeddings.json_embedding_provider_registry_loader import (
    JsonEmbeddingProviderRegistryLoader,
)


def test_load_default_includes_poc_spaces_and_models() -> None:
    config = JsonEmbeddingProviderRegistryLoader().load_default()
    assert config.fastembed.enabled is True
    assert config.ollama.enabled is True
    assert config.fastembed.model == "BAAI/bge-base-en-v1.5"
    assert config.ollama.model == "nomic-embed-text"
    assert config.default_search_space == EmbeddingSpace.OLLAMA
    assert config.request_timeout_seconds == 120

    fastembed = config.registry.resolve_binding(
        config.fastembed.provider_id, config.fastembed.model
    )
    ollama = config.registry.resolve_binding(
        config.ollama.provider_id, config.ollama.model
    )
    assert fastembed.dimensions == 768
    assert ollama.dimensions == 768
    assert fastembed.display_name == "fastembed:BAAI/bge-base-en-v1.5"
    assert ollama.display_name == "ollama:nomic-embed-text"


def test_load_rejects_unknown_active_model() -> None:
    bad_json = """
    {
      "requestTimeoutSeconds": 30,
      "defaultSearchSpace": "fastembed",
      "spaces": {
        "fastembed": {
          "enabled": true,
          "providerId": "fastembed",
          "model": "not-a-real-model"
        },
        "ollama": {
          "enabled": true,
          "providerId": "ollama",
          "model": "nomic-embed-text"
        }
      },
      "providers": [
        {
          "id": "fastembed",
          "kind": "fastembed",
          "models": [
            { "model": "BAAI/bge-base-en-v1.5", "dimensions": 768 }
          ]
        },
        {
          "id": "ollama",
          "kind": "ollama",
          "apiEndpoint": "http://localhost:11434/api",
          "models": [
            { "model": "nomic-embed-text", "dimensions": 768 }
          ]
        }
      ]
    }
    """
    with pytest.raises(ValueError, match="unknown provider/model"):
        JsonEmbeddingProviderRegistryLoader().load_json(
            bad_json, source="test.json"
        )
