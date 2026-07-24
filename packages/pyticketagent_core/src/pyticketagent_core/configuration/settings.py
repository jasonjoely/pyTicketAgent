"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """pyTicketAgent settings (``PYTICKETAGENT_*`` env vars)."""

    model_config = SettingsConfigDict(
        env_prefix="PYTICKETAGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    database_retry_max_attempts: int = 3
    database_retry_initial_delay_ms: int = 200
    database_retry_max_delay_ms: int = 2000
