from enum import Enum


class TicketState(str, Enum):
    UNASSIGNED = "unassigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
