# TRADEOFFS

## What is done

* Workspace scaffold — uv monorepo with `pyticketagent_core`, `pyticketagent_api`, `pyticketagent_generator`
* Copied/adapted artifacts: ticket scenarios, `ai-providers.json` (`PYTICKETAGENT_*` keys), DDL for database `pyTickets`
* **Generator** — Typer + Faker CLI (`--count` / `--seed`) writing `incident-tickets.json`
* **Core DAL** — asyncpg pool, `TicketRepository` (`get_by_id`, `upsert`, `search_fts`, `search_semantic`), transient DB retry
* **API** — `POST /ingest` (soft-fail upsert + counts), `GET /incidents/{id}`, `GET /search`, `GET /health`
* **LLM integration** — `ai_providers.json` registry, native `ollama` / `groq` / `google-genai` clients behind a shared `ChatClient` + factory, transient LLM retry
* **Assist-by-id** — `GET /incidents/{id}/assist` (next steps + customer draft)
* **Search assist** — `POST /assist` (hybrid candidates + LLM ranking / next steps / customer draft)
* **Dual-space embeddings at ingest (POC)** — `embedding_providers.json` holds catalog + active space config (models/enabled/timeout); FastEmbed + Ollama vectors on `tickets` (pgvector 768-d); embed-then-upsert; soft-fail per space to NULL; hash skip
* **Hybrid search (Phase B)** — FTS (`ts_rank`) + one semantic space per request, fused with RRF (k=60); `embedding_space` selector on `/search` and `/assist` (default `defaultSearchSpace`); soft-fail semantic → FTS-only; top 10 full `IncidentTicket` results

## What is not done

* Full repository surface (list/delete)
* Broader automated tests for DAL/LLM parsing (embedding + hybrid unit tests exist)
* Cross-encoder / learned re-ranker for `/search`

## Known issues and risks

* No authentication for API
* Dual embed roughly doubles ingest latency; Ollama space may be NULL if daemon/model unavailable
* One embedding space per search query (do not mix FastEmbed and Ollama vectors in one cosine ranking)
* Hybrid result cap is fixed at 10 (no pagination)

## What you would do next

1. Add unit tests for ingest validation, transient retry, and search-assist LLM JSON extraction
2. Optional: expose `limit` / pagination, or a cross-encoder re-ranker after RRF
3. Optional: surface fusion scores in API responses for debugging
