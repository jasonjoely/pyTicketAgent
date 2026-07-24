from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from pyticketagent_generator.service_scenario import ServiceScenario
from pyticketagent_generator.ticket_scenario import TicketScenario

_MAX_SERVICE_NAME_LENGTH = 30


def resolve_default_path() -> Path:
    """Return the packaged ticket_scenarios.json path."""
    resource = files("pyticketagent_generator.resources").joinpath(
        "ticket_scenarios.json"
    )
    return Path(str(resource))


def load(file_path: Path | str) -> TicketScenario:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    scenario = TicketScenario.model_validate_json(path.read_text(encoding="utf-8"))
    _validate(scenario)
    return scenario


def _validate(scenario: TicketScenario) -> None:
    if not scenario.service_scenarios:
        raise ValueError("serviceScenarios must contain at least one entry.")

    if not scenario.service_names:
        raise ValueError("serviceNames must contain at least one entry.")

    scenario_names: set[str] = set()
    for service_scenario in scenario.service_scenarios:
        _validate_service_scenario(service_scenario)
        key = service_scenario.service_name.casefold()
        if key in scenario_names:
            raise ValueError(
                "Duplicate serviceScenarios entry for service "
                f"'{service_scenario.service_name}'."
            )
        scenario_names.add(key)

    listed_names: set[str] = set()
    for service_name in scenario.service_names:
        if not service_name or not service_name.strip():
            raise ValueError("serviceNames contains a blank service name.")
        if len(service_name) > _MAX_SERVICE_NAME_LENGTH:
            raise ValueError(
                f"Service name '{service_name}' exceeds "
                f"{_MAX_SERVICE_NAME_LENGTH} characters."
            )
        listed_names.add(service_name.casefold())

    for service_name in listed_names:
        if service_name not in scenario_names:
            raise ValueError(
                f"serviceNames entry '{service_name}' has no matching "
                "serviceScenarios entry."
            )

    for service_name in scenario_names:
        if service_name not in listed_names:
            raise ValueError(
                f"serviceScenarios entry '{service_name}' is missing from "
                "serviceNames."
            )


def _validate_service_scenario(service_scenario: ServiceScenario) -> None:
    if not service_scenario.service_name or not service_scenario.service_name.strip():
        raise ValueError(
            "serviceScenarios contains an entry with a blank serviceName."
        )
    if len(service_scenario.service_name) > _MAX_SERVICE_NAME_LENGTH:
        raise ValueError(
            f"Service name '{service_scenario.service_name}' exceeds "
            f"{_MAX_SERVICE_NAME_LENGTH} characters."
        )

    _validate_array(service_scenario.service_name, "titles", service_scenario.titles)
    _validate_array(
        service_scenario.service_name, "descriptions", service_scenario.descriptions
    )
    _validate_array(
        service_scenario.service_name,
        "inProgressNotes",
        service_scenario.in_progress_notes,
    )
    _validate_array(
        service_scenario.service_name,
        "resolutionNotes",
        service_scenario.resolution_notes,
    )
    _validate_array(service_scenario.service_name, "tags", service_scenario.tags)


def _validate_array(service_name: str, field_name: str, values: list[str]) -> None:
    if not values:
        raise ValueError(
            f"serviceScenarios entry '{service_name}' must have at least one "
            f"{field_name} entry."
        )
    for value in values:
        if not value or not value.strip():
            raise ValueError(
                f"serviceScenarios entry '{service_name}' contains a blank "
                f"{field_name} entry."
            )
