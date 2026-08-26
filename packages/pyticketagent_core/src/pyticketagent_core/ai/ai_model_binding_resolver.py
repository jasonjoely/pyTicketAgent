"""Protocol for resolving the active AI provider/model binding."""

from __future__ import annotations

from typing import Protocol

from pyticketagent_core.ai.ai_model_binding import AiModelBinding


class AiModelBindingResolver(Protocol):
    """Resolve the ``AiModelBinding`` to use for chat completions."""

    def resolve_binding(self) -> AiModelBinding:
        """Return the resolved provider/model binding, or raise ValueError."""
        ...
