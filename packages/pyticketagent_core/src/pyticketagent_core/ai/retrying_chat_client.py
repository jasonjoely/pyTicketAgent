"""Chat client wrapper that retries transient provider failures."""

from __future__ import annotations

from collections.abc import Sequence

from pyticketagent_core.ai.chat_client import ChatClient
from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions
from pyticketagent_core.ai.llm_transient_error_retry import execute_with_retry
from pyticketagent_core.ai.llm_transient_retry_options import LlmTransientRetryOptions


class RetryingChatClient:
    """Delegates to an inner client with transient-error retry."""

    def __init__(
        self,
        inner: ChatClient,
        retry_options: LlmTransientRetryOptions,
    ) -> None:
        self._inner = inner
        self._retry_options = retry_options

    async def get_response(
        self,
        messages: Sequence[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        return await execute_with_retry(
            lambda: self._inner.get_response(messages, options),
            self._retry_options,
        )
