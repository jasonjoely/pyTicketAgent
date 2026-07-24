from pydantic import BaseModel, ConfigDict, Field


class ServiceScenario(BaseModel):
    """Scenario templates for one service used by the ticket generator."""

    model_config = ConfigDict(populate_by_name=True)

    service_name: str = Field(alias="serviceName")
    titles: list[str]
    descriptions: list[str]
    in_progress_notes: list[str] = Field(alias="inProgressNotes")
    resolution_notes: list[str] = Field(alias="resolutionNotes")
    tags: list[str]
