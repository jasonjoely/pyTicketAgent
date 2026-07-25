# TRADEOFFS

## What is done

* Workspace scaffold — uv monorepo with `pyticketagent_core`, `pyticketagent_api`, `pyticketagent_generator`
* Local `git init` (no GitHub remote yet)
* Copied/adapted DFAgent artifacts: ticket scenarios, `ai-providers.json` (`PYTICKETAGENT_*` keys), DDL for database `pyTickets`
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
* GitHub remote / CI

## Known issues and risks

* Generator output is not byte-identical to DFAgent.Generator (Bogus vs Faker PRNGs differ); scenario content and CLI contract match.
* Malformed ingest bodies return FastAPI **422** (DFAgent used 400).
* Ingest does not enforce DB `VARCHAR` length limits in app validation (same as DFAgent); oversized environment/service values fail at the database and are skipped.
* Groq is catalogued as `kind: openAiCompatible` (DFAgent shape) but is implemented with the native `groq` SDK.
* Search orders by `created_at DESC` (same as DFAgent), not `ts_rank`, despite the API description saying relevance order.
* Tag filter uses PostgreSQL array overlap (`&&`), matching DFAgent SQL (not strict containment of all tags).

## What you would do next

1. Add pgvector hybrid search
2. Add unit tests for ingest validation, transient retry, search-assist LLM JSON extraction, and search filtering
3. Create GitHub remote and push when ready
