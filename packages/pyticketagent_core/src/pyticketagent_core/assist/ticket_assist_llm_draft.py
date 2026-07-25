"""Parsed LLM draft for ticket assist."""

from pydantic import BaseModel, ConfigDict, Field


class TicketAssistLlmDraft(BaseModel):
    """Expected JSON shape returned by the ticket-assist prompt."""

    model_config = ConfigDict(extra="ignore")

    next_steps: list[str] = Field(min_length=1)
    customer_draft_response: str = Field(min_length=1)
