"""Response body for POST /ingest."""

from pydantic import BaseModel, Field

from pyticketagent_api.models.ingest_counts import IngestCounts
from pyticketagent_api.models.skipped_ticket_item import SkippedTicketItem


class IngestResponse(BaseModel):
    """Result of an ingest batch."""

    counts: IngestCounts = Field(description="Summary counts for the ingest operation.")
    skipped: list[SkippedTicketItem] = Field(
        description="Tickets that were skipped, with the reason each was rejected.",
    )
