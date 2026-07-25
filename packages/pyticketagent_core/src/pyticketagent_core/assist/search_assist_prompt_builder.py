"""Build chat messages for search assist."""

from __future__ import annotations

import json

from pyticketagent_core.ai.chat_message import ChatMessage
from pyticketagent_core.ai.chat_role import ChatRole
from pyticketagent_core.tickets.incident_ticket import IncidentTicket

_SYSTEM_PROMPT = """\
You are an incident support assistant helping engineers find and resolve related software operations tickets.
Respond with ONLY a raw JSON object. No markdown fences, no commentary, no text before or after the JSON.

Required JSON shape (use these exact property names):
{
  "relevant_incidents": [
    { "incident_id": 12345, "relevance": "why this ticket matches the question using only ticket facts" }
  ],
  "next_steps": ["actionable internal step 1", "actionable internal step 2"],
  "customer_draft_response": "short professional customer-facing reply"
}

Selection rules:
- When candidate incidents are provided, you MUST populate relevant_incidents with the 3 to 5 most relevant tickets
- If fewer than 3 candidates exist, select all that are relevant (at least 1 when any candidate matches the question)
- Each object MUST use incident_id (integer) and relevance (string) — do not use "id" as the only key name
- next_steps MUST contain 3 to 7 actionable internal checklist items whenever relevant_incidents is non-empty
- customer_draft_response MUST be a short professional reply (2 to 4 sentences)

Grounding rules (strict):
- Only use incident_id values from the provided candidate list
- Do not invent incident details, IDs, or resolutions not present in the candidate data
- Every relevance explanation must cite facts from that specific ticket (environment, service, title, description, tags, or resolution_summary)
- If resolution_summary is empty on a ticket, treat it as unresolved
- Never return an empty relevant_incidents array when candidates were provided and at least one ticket relates to the question
"""


class SearchAssistPromptBuilder:
    """Construct system + user messages for search-driven assist."""

    def build_messages(
        self,
        question: str,
        candidates: list[IncidentTicket],
    ) -> list[ChatMessage]:
        candidate_ids = ", ".join(str(ticket.id) for ticket in candidates)
        target_count = min(5, max(1, min(3, len(candidates))))

        candidate_json = json.dumps(
            [
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
                }
                for ticket in candidates
            ],
            indent=2,
        )

        user_message = f"""\
Question:
{question}

Candidate incident IDs (only these may appear in relevant_incidents): {candidate_ids}
Candidate count: {len(candidates)}
Select {target_count} to 5 incidents for relevant_incidents when possible.

Candidate incidents:
{candidate_json}
"""
        return [
            ChatMessage(role=ChatRole.SYSTEM, content=_SYSTEM_PROMPT),
            ChatMessage(role=ChatRole.USER, content=user_message),
        ]
