# TRADEOFFS

## What is done

* Workspace scaffold — uv monorepo with `pyticketagent_core`, `pyticketagent_api`, `pyticketagent_generator`
* Local `git init` (no GitHub remote yet)
* Copied/adapted DFAgent artifacts: ticket scenarios, `ai-providers.json` (`PYTICKETAGENT_*` keys), DDL for database `pyTickets`
* **Generator** — Typer + Faker CLI (`--count` / `--seed`) writing `incident-tickets.json`
* **Core DAL** — asyncpg pool, `TicketRepository` (`get_by_id`, `upsert`), transient DB retry
* **API** — `POST /ingest` (soft-fail upsert + counts), `GET /incidents/{id}`, `GET /health`

## What is not done

* Search and Assist endpoints
* Full repository surface (list/search/delete)
* LLM assist / provider wiring
* pgvector semantic search
* Automated tests for ingest/DAL
* GitHub remote / CI

## Known issues and risks

* Generator output is not byte-identical to DFAgent.Generator (Bogus vs Faker PRNGs differ); scenario content and CLI contract match.
* Malformed ingest bodies return FastAPI **422** (DFAgent used 400).
* Ingest does not enforce DB `VARCHAR` length limits in app validation (same as DFAgent); oversized environment/service values fail at the database and are skipped.

## What you would do next

1. Port Search endpoints against `pyTickets` full-text search
2. Port Assist/LLM endpoints
3. Add pgvector hybrid search
4. Add unit tests for ingest validation and transient retry
5. Create GitHub remote and push when ready
