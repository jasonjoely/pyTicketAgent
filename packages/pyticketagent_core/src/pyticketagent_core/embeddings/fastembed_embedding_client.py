"""FastEmbed in-process embedding client."""

from __future__ import annotations

import asyncio
import logging

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class FastEmbedEmbeddingClient:
    """Embeddings via ``fastembed.TextEmbedding`` (CPU/ONNX)."""

    def __init__(self, model_name: str, *, expected_dimensions: int) -> None:
        self._model_name = model_name
        self._expected_dimensions = expected_dimensions
        self._model: TextEmbedding | None = None

    def _ensure_model(self) -> TextEmbedding:
        if self._model is None:
            try:
                logger.info(
                    "Loading FastEmbed model %s (first use may download weights)",
                    self._model_name,
                )
                self._model = TextEmbedding(model_name=self._model_name)
            except Exception:
                logger.error(
                    "Failed to initialize FastEmbed model %s",
                    self._model_name,
                    exc_info=True,
                )
                raise
        return self._model

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        vectors: list[list[float]] = []
        for vector in model.embed(texts):
            as_list = [float(v) for v in vector]
            if len(as_list) != self._expected_dimensions:
                raise ValueError(
                    f"FastEmbed model '{self._model_name}' returned "
                    f"{len(as_list)} dimensions; expected {self._expected_dimensions}."
                )
            vectors.append(as_list)
        return vectors

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts)
