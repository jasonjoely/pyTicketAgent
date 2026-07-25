"""Extract a JSON object from noisy LLM text."""

from __future__ import annotations

import re

_MARKDOWN_FENCE_REGEX = re.compile(
    r"```(?:json)?\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)
_JSON_OBJECT_REGEX = re.compile(r"\{[\s\S]*\}")


class LlmResponseJsonExtractor:
    """Pull JSON out of markdown fences or surrounding prose."""

    @staticmethod
    def extract_json(response_text: str) -> str:
        trimmed = response_text.strip()

        fence_match = _MARKDOWN_FENCE_REGEX.search(trimmed)
        if fence_match:
            return fence_match.group(1).strip()

        object_match = _JSON_OBJECT_REGEX.search(trimmed)
        if object_match:
            return object_match.group(0).strip()

        return trimmed
