"""Active binding for one embedding space from API config JSON."""

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingSpaceBindingConfig(BaseModel):
    """Enabled flag + provider/model for one dual-space column group."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    enabled: bool = True
    provider_id: str = Field(alias="providerId")
    model: str
