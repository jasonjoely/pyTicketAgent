"""Selectable model entry under an AI provider."""

from pydantic import BaseModel, ConfigDict


class AiModelDefinition(BaseModel):
    """A model name advertised by a provider."""

    model_config = ConfigDict(extra="forbid")

    model: str
