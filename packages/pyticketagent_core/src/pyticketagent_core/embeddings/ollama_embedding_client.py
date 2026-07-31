"""Ollama embedding client using the native ollama SDK."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from ollama import AsyncClient

logger = logging.getLogger(__name__)


class OllamaEmbeddingClient:
    """Embeddings via ``ollama.AsyncClient.embed``."""

    def __init__(
        self,
        api_endpoint: str,
        model_name: str,
        *,
        expected_dimensions: int,
        timeout_seconds: float,
    ) -> None:
        self._model_name = model_name
        self._expected_dimensions = expected_dimensions
        host = _ollama_host(api_endpoint)
        self._client = AsyncClient(host=host, timeout=timeout_seconds)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embed(
            model=self._model_name,
            input=texts,
        )
        raw = response.embeddings
        if raw is None:
            raise ValueError(
                f"Ollama model '{self._model_name}' returned no embeddings."
            )

        vectors: list[list[float]] = []
        for vector in raw:
            as_list = [float(v) for v in vector]
            if len(as_list) != self._expected_dimensions:
                raise ValueError(
                    f"Ollama model '{self._model_name}' returned "
                    f"{len(as_list)} dimensions; expected {self._expected_dimensions}."
                )
            vectors.append(as_list)

        if len(vectors) != len(texts):
            raise ValueError(
                f"Ollama model '{self._model_name}' returned {len(vectors)} "
                f"embeddings for {len(texts)} texts."
            )
        return vectors


def _ollama_host(api_endpoint: str) -> str:
    """Convert catalog endpoint (often ``.../api``) to an ollama SDK host URL."""
    trimmed = api_endpoint.strip().rstrip("/")
    if trimmed.casefold().endswith("/api"):
        trimmed = trimmed[: -len("/api")]
    parsed = urlparse(trimmed)
    if not parsed.scheme or not parsed.netloc:
        return trimmed or "http://localhost:11434"
    return f"{parsed.scheme}://{parsed.netloc}"
