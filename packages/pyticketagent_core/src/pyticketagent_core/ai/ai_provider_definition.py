"""AI provider definition from the providers catalog."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.ai.ai_model_definition import AiModelDefinition
from pyticketagent_core.ai.ai_provider_kind import AiProviderKind


class AiProviderDefinition(BaseModel):
    """One provider entry from ``ai_providers.json``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    kind: AiProviderKind
    api_endpoint: str | None = Field(default=None, alias="apiEndpoint")
    api_key: str | None = Field(default=None, alias="apiKey")
    models: list[AiModelDefinition] = Field(default_factory=list)
