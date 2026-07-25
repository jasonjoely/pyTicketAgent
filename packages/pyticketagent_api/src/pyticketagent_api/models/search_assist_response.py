"""Response model for POST /assist."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_api.models.relevant_incident import RelevantIncident


class SearchAssistResponse(BaseModel):
    """AI assist payload derived from search candidates."""

    model_config = ConfigDict(extra="forbid")

    candidate_count: int = Field(
        description="Number of incidents considered as candidates before LLM ranking."
    )
    relevant_incidents: list[RelevantIncident] = Field(
        description="Incidents the LLM identified as most relevant to the question."
    )
    next_steps: list[str] = Field(
        description="Recommended troubleshooting steps based on relevant incidents."
    )
    customer_draft_response: str = Field(
        description="Draft response suitable for sending to a customer."
    )
