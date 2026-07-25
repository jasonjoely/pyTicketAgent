"""Common async chat client protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_options import ChatOptions


class ChatClient(Protocol):
    """Async chat completion client used by Assist services."""

    async def get_response(
        self,
        messages: Sequence[ChatMessage],
        options: ChatOptions | None = None,
    ) -> str:
        """Return the assistant text for the given messages."""
        ...
