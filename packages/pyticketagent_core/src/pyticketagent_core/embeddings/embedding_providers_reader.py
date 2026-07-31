"""Reads the Embedding Providers Configuration file ``embedding_providers.json``."""

from __future__ import annotations

from importlib import resources


def read_embedding_providers_json() -> str:
    """Read the packaged embedding providers catalog as UTF-8 text."""
    return (
        resources.files("pyticketagent_core")
        .joinpath("resources/embedding_providers.json")
        .read_text(encoding="utf-8")
    )
