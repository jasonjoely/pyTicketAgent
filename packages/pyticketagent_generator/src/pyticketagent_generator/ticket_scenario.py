from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_generator.service_scenario import ServiceScenario


class TicketScenario(BaseModel):
    """Root scenario file loaded from ticket_scenarios.json."""

    model_config = ConfigDict(populate_by_name=True)

    service_names: list[str] = Field(alias="serviceNames")
    service_scenarios: list[ServiceScenario] = Field(alias="serviceScenarios")
