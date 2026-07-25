"""Request body for POST /assist."""

from pydantic import BaseModel, ConfigDict, Field


class AssistRequest(BaseModel):
    """Natural-language question plus optional search filters."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        description="Natural-language question describing the incident or issue to investigate."
    )
    environment: str | None = Field(
        default=None,
        description="Optional filter: deployment environment (e.g. production, staging).",
    )
    service: str | None = Field(
        default=None,
        description="Optional filter: service or application name.",
    )
    severity: int | None = Field(
        default=None,
        description="Optional filter: severity level (1-5).",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional filter: tags that must all be present on matching incidents.",
    )
