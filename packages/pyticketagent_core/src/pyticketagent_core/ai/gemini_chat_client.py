"""Gemini chat client using the native google-genai SDK."""

from __future__ import annotations

from collections.abc import Sequence

from google import genai
from google.genai import types

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.ai.chat_role import ChatRole
from pyticketagent_core.ai.gemini_thinking_config_factory import GeminiThinkingConfigFactory


class GeminiChatClient:
    """Chat completions via ``google.genai.Client`` (async)."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        timeout_seconds: float,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError(
                "Gemini API key is required. Set the environment variable "
                "configured in ai_providers.json."
            )
        self._model_name = model_name
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
            ),
        )

    async def get_response(
        self,
        messages: Sequence[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        opts = options or ChatOptions()
        system_parts = [
            message.content
            for message in messages
            if message.role == ChatRole.SYSTEM and message.content.strip()
        ]
        contents = [
            types.Content(
                role="model" if message.role == ChatRole.ASSISTANT else "user",
                parts=[types.Part(text=message.content)],
            )
            for message in messages
            if message.role != ChatRole.SYSTEM and message.content.strip()
        ]

        config = types.GenerateContentConfig(
            max_output_tokens=opts.max_output_tokens,
            temperature=opts.temperature,
            thinking_config=GeminiThinkingConfigFactory.for_model(self._model_name),
        )
        if system_parts:
            config.system_instruction = types.Content(
                parts=[types.Part(text=text) for text in system_parts]
            )

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=config,
        )
        text = response.text
        return text if text is not None else ""
