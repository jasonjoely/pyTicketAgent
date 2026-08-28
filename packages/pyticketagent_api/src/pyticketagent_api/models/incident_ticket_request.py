"""Loose ingest request DTO (nullable fields for soft-fail validation)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.tickets.ticket_state import TicketState


class IncidentTicketRequest(BaseModel):
    """Ingest payload item. Validation beyond shape is done in the ingest service."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(default=0, description="Unique ticket identifier. Must be a positive integer.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.fromtimestamp(0),
        description="When the incident was created.",
    )
    environment: str | None = Field(
        default=None,
        description="Deployment environment (e.g. production, staging).",
    )
    service: str | None = Field(
        default=None,
        description="Service or application affected by the incident.",
    )
    title: str | None = Field(
        default=None,
        description="Short summary of the incident.",
    )
    description: str | None = Field(
        default=None,
        description="Detailed incident description including symptoms and impact.",
    )
    resolution_summary: str | None = Field(
        default=None,
        description="How the incident was resolved.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Labels for categorizing and filtering the incident.",
    )
    severity: int | None = Field(
        default=None,
        description="Severity level from 0 (lowest) upward.",
    )
    status: TicketState | None = Field(
        default=None,
        description="Current status of the incident.",
    )
