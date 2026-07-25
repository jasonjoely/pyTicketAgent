"""Build chat messages for ticket assist."""

from __future__ import annotations

import json

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_role import ChatRole
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

_SYSTEM_PROMPT = """\
You are an incident support assistant helping engineers resolve software operations tickets.
Respond with ONLY a raw JSON object. No markdown fences, no commentary.

The JSON object must have these properties:
- next_steps: array of 3 to 7 short, actionable internal checklist items for the engineer
- customer_draft_response: a short, professional, customer-facing draft response (2 to 4 sentences)

Base your recommendations on the ticket details provided. If resolution_summary is empty, treat the ticket as unresolved.
"""


class TicketAssistPromptBuilder:
    """Construct system + user messages for assist-by-id."""

    def build_messages(self, ticket: IncidentTicket) -> list[ChatMessage]:
        ticket_json = json.dumps(
            {
                "id": ticket.id,
                "created_at": ticket.created_at.isoformat(),
                "environment": ticket.environment,
                "service": ticket.service,
                "title": ticket.title,
                "description": ticket.description,
                "severity": ticket.severity,
                "tags": ticket.tags,
                "resolution_summary": ticket.resolution_summary,
            },
            indent=2,
        )
        return [
            ChatMessage(role=ChatRole.SYSTEM, content=_SYSTEM_PROMPT),
            ChatMessage(
                role=ChatRole.USER,
                content=f"Assist with this incident ticket:\n{ticket_json}",
            ),
        ]
