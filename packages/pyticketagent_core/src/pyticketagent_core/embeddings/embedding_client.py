"""Protocol for embedding clients."""

from __future__ import annotations

from typing import Protocol


class EmbeddingClient(Protocol):
    """Generate dense vectors for one or more texts."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order."""
        ...
