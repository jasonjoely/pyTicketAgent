"""Options for a chat completion request."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatOptions:
    """Provider-agnostic chat options."""

    max_output_tokens: int = 1024
    temperature: float | None = None
