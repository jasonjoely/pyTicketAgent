"""Single hit in a search response."""

from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    """Compact search hit for an incident ticket."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="Incident ticket ID.")
    title: str = Field(description="Incident title.")
    short_snippet: str = Field(
        description="Brief excerpt from the incident description or resolution."
    )
