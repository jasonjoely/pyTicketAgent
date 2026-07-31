"""Selectable model entry under an embedding provider."""

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingModelDefinition(BaseModel):
    """A model name and output dimensions advertised by a provider."""

    model_config = ConfigDict(extra="forbid")

    model: str
    dimensions: int = Field(gt=0)
