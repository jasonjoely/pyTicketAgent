"""Chat message passed to provider clients."""

from dataclasses import dataclass

from pyticketagent_core.ai.chat_role import ChatRole


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A single chat message."""

    role: ChatRole
    content: str
