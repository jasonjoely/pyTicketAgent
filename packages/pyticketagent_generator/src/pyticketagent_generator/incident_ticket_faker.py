from __future__ import annotations

from datetime import datetime, timedelta, timezone

from faker import Faker

from pyticketagent_core.tickets.incident_ticket import IncidentTicket
from pyticketagent_generator.ticket_scenario import TicketScenario
from pyticketagent_generator.ticket_state import TicketState


class IncidentTicketFaker:
    """Generates realistic incident tickets from scenario templates."""

    def __init__(self, scenarios: TicketScenario) -> None:
        self._scenarios = scenarios

    def generate(self, count: int, seed: int) -> list[IncidentTicket]:
        if count <= 0:
            return []

        faker = Faker(locale="en")
        faker.seed_instance(seed)
        anchor = _anchor_from_seed(seed)
        base_id = faker.random_int(100_000, 900_000)
        tickets: list[IncidentTicket] = []

        for i in range(count):
            scenario = faker.random_element(self._scenarios.service_scenarios)
            roll = faker.random.random()
            if roll < 0.30:
                state = TicketState.UNASSIGNED
            elif roll < 0.70:
                state = TicketState.IN_PROGRESS
            else:
                state = TicketState.RESOLVED

            if state is TicketState.UNASSIGNED:
                resolution = ""
            elif state is TicketState.IN_PROGRESS:
                resolution = faker.random_element(scenario.in_progress_notes)
            else:
                resolution = (
                    faker.random_element(scenario.in_progress_notes)
                    + "\r\n"
                    + faker.random_element(scenario.resolution_notes)
                )

            offset_seconds = faker.random.uniform(0, timedelta(days=30).total_seconds())
            created_at = anchor - timedelta(seconds=offset_seconds)

            tickets.append(
                IncidentTicket(
                    id=base_id + i,
                    created_at=created_at,
                    environment=faker.random_element(["dev", "qa", "stage", "prod"]),
                    service=scenario.service_name,
                    title=faker.random_element(scenario.titles),
                    description=faker.random_element(scenario.descriptions),
                    resolution_summary=resolution,
                    tags=_pick_tags(faker, scenario.tags),
                    severity=faker.random_int(0, 4),
                )
            )

        return tickets


def _anchor_from_seed(seed: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=abs(seed) % 365)


def _pick_tags(faker: Faker, tags: list[str]) -> list[str]:
    tag_count = min(faker.random_int(1, 4), len(tags))
    picked = [faker.random_element(tags) for _ in range(tag_count)]
    seen: set[str] = set()
    result: list[str] = []
    for tag in picked:
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            result.append(tag.lower())
    return result
