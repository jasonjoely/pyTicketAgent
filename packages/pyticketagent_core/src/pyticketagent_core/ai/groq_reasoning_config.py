"""Reasoning request tweaks for Groq models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GroqReasoningConfig:
    """Groq-specific reasoning controls for a model."""

    reasoning_effort: str | None
    include_reasoning: bool
