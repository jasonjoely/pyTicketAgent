"""Dual embedding space identifiers for the POC."""

from enum import Enum


class EmbeddingSpace(str, Enum):
    """Which embedding column group / provider path to use."""

    FASTEMBED = "fastembed"
    OLLAMA = "ollama"
