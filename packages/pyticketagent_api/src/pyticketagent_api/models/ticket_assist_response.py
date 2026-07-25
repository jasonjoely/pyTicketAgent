"""Response model for GET /incidents/{id}/assist."""

from pydantic import BaseModel, ConfigDict, Field


class TicketAssistResponse(BaseModel):
    """AI assist payload for a single incident."""

    model_config = ConfigDict(extra="forbid")

    ticket_id: int = Field(description="ID of the incident that was analyzed.")
    next_steps: list[str] = Field(
        description="Recommended troubleshooting steps for the incident."
    )
    customer_draft_response: str = Field(
        description="Draft response suitable for sending to a customer."
    )
    provider: str = Field(
        description="LLM provider used to generate the assist response."
    )
    model: str = Field(description="LLM model used to generate the assist response.")
