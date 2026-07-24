"""Details for a ticket skipped during ingest."""

from pydantic import BaseModel, Field


class SkippedTicketItem(BaseModel):
    """A ticket that was not ingested, with the reason."""

    id: int = Field(description="ID of the ticket that was skipped.")
    reason: str = Field(description="Why the ticket was not ingested.")
