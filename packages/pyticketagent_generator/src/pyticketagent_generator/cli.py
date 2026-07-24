from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pyticketagent_generator.incident_ticket_faker import IncidentTicketFaker
from pyticketagent_generator import ticket_scenario_loader

_DEFAULT_COUNT = 50
_DEFAULT_SEED = 42
_MAX_COUNT = 500
_OUTPUT_FILE_NAME = "incident-tickets.json"

app = typer.Typer(
    help="Generates sample incident ticket data using Faker.",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Number of incident tickets (0-500)."),
    ] = _DEFAULT_COUNT,
    seed: Annotated[
        int,
        typer.Option("--seed", "-s", help="Random seed for reproducible output."),
    ] = _DEFAULT_SEED,
) -> None:
    if count < 0 or count > _MAX_COUNT:
        typer.echo(
            f"Invalid count: {count}. Count must be between 0 and {_MAX_COUNT}.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        scenario_path = ticket_scenario_loader.resolve_default_path()
        scenarios = ticket_scenario_loader.load(scenario_path)
        faker = IncidentTicketFaker(scenarios)
        tickets = faker.generate(count, seed)
        output_path = Path.cwd() / _OUTPUT_FILE_NAME
        _write_tickets(output_path, tickets)

        typer.echo(f"Generated {len(tickets)} incident ticket(s).")
        typer.echo(f"Seed: {seed}")
        typer.echo(f"Output: {output_path.resolve()}")
    except Exception as ex:  # noqa: BLE001 — surface CLI errors like DFAgent
        typer.echo(str(ex), err=True)
        raise typer.Exit(code=1) from ex


def _write_tickets(output_path: Path, tickets: list) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [ticket.model_dump(mode="json") for ticket in tickets]
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


if __name__ == "__main__":
    app()
