# TRADEOFFS

## What is done

* Workspace scaffold — uv monorepo with `pyticketagent_core`, `pyticketagent_api`, `pyticketagent_generator`
* Copied/adapted artifacts: ticket scenarios, `ai-providers.json` (`PYTICKETAGENT_*` keys), DDL for database `pyTickets`
* **Generator** — Typer + Faker CLI (`--count` / `--seed`) writing `incident-tickets.json`
* **Core DAL** — asyncpg pool, `TicketRepository` (`get_by_id`, `upsert`, `search`), transient DB retry
* **API** — `POST /ingest` (soft-fail upsert + counts), `GET /incidents/{id}`, `GET /search`, `GET /health`
* **LLM integration** — `ai_providers.json` registry, native `ollama` / `groq` / `google-genai` clients behind a shared `ChatClient` + factory, transient LLM retry
* **Assist-by-id** — `GET /incidents/{id}/assist` (next steps + customer draft)
* **Search assist** — `POST /assist` (FTS candidates + LLM ranking / next steps / customer draft)

## What is not done

* Full repository surface (list/delete)
* pgvector semantic search
* Automated tests for ingest/DAL/LLM parsing

## Known issues and risks

* No authentication for API

## What you would do next

1. Add pgvector hybrid search
2. Add unit tests for ingest validation, transient retry, search-assist LLM JSON extraction, and search filtering
