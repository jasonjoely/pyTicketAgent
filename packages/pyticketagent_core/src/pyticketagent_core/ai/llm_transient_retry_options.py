"""Retry policy for transient LLM API failures."""

from __future__ import annotations

from dataclasses import dataclass

from pyticketagent_core.configuration.settings import Settings


@dataclass(frozen=True, slots=True)
class LlmTransientRetryOptions:
    """Exponential-backoff retry settings for LLM calls."""

    max_attempts: int = 5
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000

    @classmethod
    def from_settings(cls, settings: Settings) -> LlmTransientRetryOptions:
        return cls(
            max_attempts=max(0, settings.llm_transient_retry_max_attempts),
            initial_delay_ms=max(0, settings.llm_transient_retry_initial_delay_ms),
            max_delay_ms=max(0, settings.llm_transient_retry_max_delay_ms),
        )
