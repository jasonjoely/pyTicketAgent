"""Groq chat client using the native groq SDK."""

from __future__ import annotations

from collections.abc import Sequence

from groq import AsyncGroq

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.ai.groq_reasoning_config_factory import GroqReasoningConfigFactory


class GroqChatClient:
    """Chat completions via ``groq.AsyncGroq``."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        timeout_seconds: float,
        base_url: str | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Groq API key is required.")
        self._model_name = model_name
        kwargs: dict[str, object] = {
            "api_key": api_key,
            "timeout": timeout_seconds,
        }
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncGroq(**kwargs)

    async def get_response(
        self,
        messages: Sequence[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        opts = options or ChatOptions()
        create_kwargs: dict[str, object] = {
            "model": self._model_name,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            "max_tokens": opts.max_output_tokens,
        }
        if opts.temperature is not None:
            create_kwargs["temperature"] = opts.temperature

        reasoning = GroqReasoningConfigFactory.for_model(self._model_name)
        if reasoning is not None:
            if reasoning.reasoning_effort is not None:
                create_kwargs["reasoning_effort"] = reasoning.reasoning_effort
            create_kwargs["include_reasoning"] = reasoning.include_reasoning

        response = await self._client.chat.completions.create(**create_kwargs)
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message is None:
            return ""
        content = choice.message.content
        return content if content is not None else ""
