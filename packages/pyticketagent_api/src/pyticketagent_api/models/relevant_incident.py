"""Relevant incident cited in a search-assist response."""

from pydantic import BaseModel, ConfigDict, Field


class RelevantIncident(BaseModel):
    """One incident the LLM identified as relevant to the question."""

    model_config = ConfigDict(extra="forbid")

    incident_id: int = Field(description="ID of a relevant incident.")
    relevance: str = Field(
        description="Brief explanation of why this incident is relevant to the question."
    )
