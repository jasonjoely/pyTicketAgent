"""Resolved provider + model binding for embeddings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmbeddingModelBinding:
    """Active provider id and model name for an embedding call."""

    provider_id: str
    model: str
    dimensions: int

    @property
    def display_name(self) -> str:
        return f"{self.provider_id}:{self.model}"
