"""AI provider kind enumeration."""

from enum import Enum


class AiProviderKind(str, Enum):
    """Provider backend kinds from ``ai_providers.json``."""

    OLLAMA = "ollama"
    OPEN_AI_COMPATIBLE = "openAiCompatible"
    GEMINI = "gemini"
