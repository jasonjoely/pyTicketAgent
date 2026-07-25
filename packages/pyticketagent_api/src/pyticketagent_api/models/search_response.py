"""Response model for GET /search."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_api.models.search_result_item import SearchResultItem


class SearchResponse(BaseModel):
    """Full-text search results."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(description="Total number of matching incidents.")
    results: list[SearchResultItem] = Field(
        description="Search hits ordered by relevance."
    )
