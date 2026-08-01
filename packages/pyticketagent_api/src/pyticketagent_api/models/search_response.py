"""Response model for GET /search."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.tickets.incident_ticket import IncidentTicket


class SearchResponse(BaseModel):
    """Hybrid search results with full incident tickets."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(description="Total number of matching incidents returned.")
    results: list[IncidentTicket] = Field(
        description="Search hits ordered by hybrid relevance (RRF)."
    )
