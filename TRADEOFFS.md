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
* **Dual-space embeddings at ingest (POC)** — `embedding_providers.json` holds catalog + active space config (models/enabled/timeout); FastEmbed + Ollama vectors on `tickets` (pgvector 768-d); embed-then-upsert; soft-fail per space to NULL; hash skip; logging only (no search yet)

## What is not done

* Full repository surface (list/delete)
* pgvector hybrid / semantic search (Phase B) — columns are written; query path not wired
* Broader automated tests for DAL/LLM parsing (embedding unit tests exist)

## Known issues and risks

* No authentication for API
* Dual embed roughly doubles ingest latency; Ollama space may be NULL if daemon/model unavailable
* One embedding space per search query (do not mix FastEmbed and Ollama vectors in one cosine ranking)

## What you would do next

1. Add pgvector hybrid search with `embedding_space=fastembed|ollama` selector
2. Add unit tests for ingest validation, transient retry, search-assist LLM JSON extraction, and search filtering
