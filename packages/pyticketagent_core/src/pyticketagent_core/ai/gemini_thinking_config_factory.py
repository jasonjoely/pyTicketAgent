"""Gemini thinking config that minimizes unused thought tokens."""

from __future__ import annotations

from google.genai import types


class GeminiThinkingConfigFactory:
    """Build ThinkingConfig for the given Gemini model name."""

    @staticmethod
    def for_model(model_name: str) -> types.ThinkingConfig | None:
        if not model_name or not model_name.strip():
            return None

        # Disable / minimize thoughts — they count toward token usage and are
        # not needed for Assist JSON responses.
        if "2.5" in model_name:
            return types.ThinkingConfig(thinking_budget=0, include_thoughts=False)

        return types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL,
            include_thoughts=False,
        )
