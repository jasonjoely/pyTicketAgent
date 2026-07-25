"""Resolved provider + model binding."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AiModelBinding:
    """Active provider id and model name for an LLM call."""

    provider_id: str
    model: str

    @property
    def display_name(self) -> str:
        return f"{self.provider_id}/{self.model}"
