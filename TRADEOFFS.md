# TRADEOFFS

## What is done

* Workspace scaffold — uv monorepo with `pyticketagent_core`, `pyticketagent_api`, `pyticketagent_generator`
* Local `git init` (no GitHub remote yet)
* Copied/adapted DFAgent artifacts: ticket scenarios, `ai-providers.json` (`PYTICKETAGENT_*` keys), DDL for database `pyTickets`
* **Generator** — Typer + Faker CLI (`--count` / `--seed`) writing `incident-tickets.json`
* API stub — FastAPI app with `/health` only

## What is not done

* Full API (ingest, search, assist)
* asyncpg data access layer
* LLM assist / provider wiring
* pgvector semantic search
* GitHub remote / CI

## Known issues and risks

* Generator output is not byte-identical to DFAgent.Generator (Bogus vs Faker PRNGs differ); scenario content and CLI contract match.
* API package is a stub until the next milestone.

## What you would do next

1. Implement Core DAL (asyncpg) + FastAPI ingest/search against `pyTickets`
2. Port Assist/LLM endpoints
3. Add pgvector hybrid search
4. Create GitHub remote and push when ready
