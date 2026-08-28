"""Request body for POST /assist."""

from pydantic import BaseModel, ConfigDict, Field

from pyticketagent_core.embeddings.embedding_space import EmbeddingSpace
from pyticketagent_core.tickets.ticket_state import TicketState


class AssistRequest(BaseModel):
    """Natural-language question plus optional search filters."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(
        description="Natural-language question describing the incident or issue to investigate."
    )
    environment: str | None = Field(
        default=None,
        description="Optional filter: deployment environment (e.g. production, staging).",
    )
    service: str | None = Field(
        default=None,
        description="Optional filter: service or application name.",
    )
    severity: int | None = Field(
        default=None,
        description="Optional filter: severity level (1-5).",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional filter: tags that must all be present on matching incidents.",
    )
    status: TicketState | None = Field(
        default=None,
        description="Optional filter: ticket status.",
    )
    embedding_space: EmbeddingSpace | None = Field(
        default=None,
        description=(
            "Optional embedding space for hybrid candidate retrieval "
            "(fastembed or ollama). Omitting uses defaultSearchSpace from config."
        ),
    )
