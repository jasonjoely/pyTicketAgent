"""Outcome of a ticket upsert operation."""

from enum import Enum


class UpsertOutcome(Enum):
    """Whether an upsert inserted a new row or updated an existing one."""

    CREATED = "created"
    UPDATED = "updated"
