"""Embedding provider kind enumeration."""

from enum import Enum


class EmbeddingProviderKind(str, Enum):
    """Provider backend kinds from ``embedding_providers.json``."""

    FASTEMBED = "fastembed"
    OLLAMA = "ollama"
