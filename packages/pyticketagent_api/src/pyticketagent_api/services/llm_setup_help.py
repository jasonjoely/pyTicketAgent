"""User-facing guidance when LLM configuration is missing or invalid."""


class LlmSetupHelp:
    """Enrich Assist error messages with setup instructions."""

    _SETUP_INSTRUCTIONS = (
        "Set PYTICKETAGENT_LLM_PROVIDER (ollama|groq|gemini) and PYTICKETAGENT_LLM_MODEL. "
        "For groq: set PYTICKETAGENT_GROQ_API_KEY. For gemini: set PYTICKETAGENT_GEMINI_API_KEY. "
        "For ollama: ensure Ollama is running at http://localhost:11434. "
        "Then restart the API and retry."
    )

    @classmethod
    def enrich(cls, message: str) -> str:
        return f"{message} {cls._SETUP_INSTRUCTIONS}"

    @classmethod
    def timeout_message(cls, timeout_seconds: int) -> str:
        return (
            f"LLM request timed out after {timeout_seconds} seconds. "
            "Increase PYTICKETAGENT_LLM_REQUEST_TIMEOUT_SECONDS if needed, "
            f"or check that your provider is running. {cls._SETUP_INSTRUCTIONS}"
        )
