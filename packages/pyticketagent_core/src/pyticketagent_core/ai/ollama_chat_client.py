"""Ollama chat client using the native ollama SDK."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urlparse

from ollama import AsyncClient

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions


class OllamaChatClient:
    """Chat completions via ``ollama.AsyncClient``."""

    def __init__(
        self,
        api_endpoint: str,
        model_name: str,
        *,
        timeout_seconds: float,
    ) -> None:
        self._model_name = model_name
        host = _ollama_host(api_endpoint)
        self._client = AsyncClient(host=host, timeout=timeout_seconds)

    async def get_response(
        self,
        messages: Sequence[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        opts = options or ChatOptions()
        ollama_options: dict[str, object] = {
            "num_predict": opts.max_output_tokens,
        }
        if opts.temperature is not None:
            ollama_options["temperature"] = opts.temperature

        response = await self._client.chat(
            model=self._model_name,
            messages=[
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            think=False,
            options=ollama_options,
        )
        content = response.message.content
        return content if content is not None else ""


def _ollama_host(api_endpoint: str) -> str:
    """Convert catalog endpoint (often ``.../api``) to an ollama SDK host URL."""
    trimmed = api_endpoint.strip().rstrip("/")
    if trimmed.casefold().endswith("/api"):
        trimmed = trimmed[: -len("/api")]
    parsed = urlparse(trimmed)
    if not parsed.scheme or not parsed.netloc:
        return trimmed or "http://localhost:11434"
    return f"{parsed.scheme}://{parsed.netloc}"
