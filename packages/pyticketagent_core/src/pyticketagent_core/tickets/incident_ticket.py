from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.tickets.ticket_state import TicketState


class IncidentTicket(BaseModel):
    """Incident ticket domain model (snake_case JSON)."""

    model_config = ConfigDict(
        populate_by_name=True,
        ser_json_timedelta="iso8601",
    )

    id: int = Field(description="Unique incident ticket identifier.")
    created_at: datetime = Field(description="When the incident was created.")
    environment: str = Field(
        description="Deployment environment (e.g. production, staging)."
    )
    service: str = Field(
        description="Service or application affected by the incident."
    )
    title: str = Field(description="Short summary of the incident.")
    description: str = Field(
        description="Detailed incident description including symptoms and impact."
    )
    resolution_summary: str = Field(
        description="How the incident was resolved."
    )
    tags: list[str] = Field(
        description="Labels for categorizing and filtering the incident."
    )
    severity: int = Field(
        description="Severity level from 0 (lowest) upward."
    )
    status: TicketState = Field(
        description="Current status of the incident."
    )
