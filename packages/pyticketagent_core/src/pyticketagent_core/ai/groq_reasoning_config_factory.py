"""Build Groq reasoning options that minimize unused thinking tokens."""

from __future__ import annotations

from pyticketagent_core.ai.groq_reasoning_config import GroqReasoningConfig


class GroqReasoningConfigFactory:
    """Select reasoning_effort / include_reasoning based on model name."""

    @staticmethod
    def for_model(model_name: str) -> GroqReasoningConfig | None:
        if not model_name or not model_name.strip():
            return None

        lowered = model_name.casefold()
        if "qwen" in lowered:
            return GroqReasoningConfig(
                reasoning_effort="none",
                include_reasoning=False,
            )
        if "gpt-oss" in lowered:
            return GroqReasoningConfig(
                reasoning_effort="low",
                include_reasoning=False,
            )
        return None
