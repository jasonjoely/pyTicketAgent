"""Summary counts for an ingest operation."""

from pydantic import BaseModel, Field


class IngestCounts(BaseModel):
    """Number of tickets ingested, updated, and skipped."""

    ingested: int = Field(default=0, description="Number of new tickets inserted.")
    updated: int = Field(default=0, description="Number of existing tickets updated.")
    skipped: int = Field(
        default=0,
        description="Number of tickets skipped due to validation or database errors.",
    )
