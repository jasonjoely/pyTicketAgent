from enum import Enum


class TicketState(Enum):
    UNASSIGNED = "unassigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
