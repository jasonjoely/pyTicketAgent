"""Raised when an LLM assist response cannot be parsed."""


class TicketAssistParseException(Exception):
    """LLM returned empty or invalid assist JSON."""
