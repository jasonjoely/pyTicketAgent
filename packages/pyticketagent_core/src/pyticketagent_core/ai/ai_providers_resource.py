"""Locate the packaged ``ai_providers.json`` catalog."""

from __future__ import annotations

from importlib import resources


def read_ai_providers_json() -> str:
    """Read the packaged providers catalog as UTF-8 text."""
    return (
        resources.files("pyticketagent_core")
        .joinpath("resources/ai_providers.json")
        .read_text(encoding="utf-8")
    )
