# pyTicketAgent

Python implementation of an Incident Ticket Management System with PostgreSQL full-text search, dual-space vector embeddings at ingest (pgvector), and LLM-assisted troubleshooting.

| Package | Purpose |
|---------|---------|
| `pyticketagent_core` | Shared models, data access (asyncpg), AI helpers |
| `pyticketagent_api` | FastAPI REST API (Ingest, Search, Assist) |
| `pyticketagent_generator` | CLI that generates sample incident ticket JSON |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 12+ with [pgvector](https://github.com/pgvector/pgvector) (for API; not required for Generator)
- An LLM provider for Assist endpoints ([Ollama](https://ollama.com/), [Groq](https://groq.com/), or [Google Gemini](https://ai.google.dev/))
- For the Ollama embedding space at ingest: `ollama pull nomic-embed-text` (FastEmbed downloads weights on first use)

## Getting started

```powershell
cd C:\Users\jason\source\repos\pyTicketAgent
uv sync
```

### Generate sample tickets

```powershell
uv run pyticketagent-generator
# or:
uv run python -m pyticketagent_generator
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--count` | `-c` | `50` | Number of tickets (0–500) |
| `--seed` | `-s` | `42` | Random seed for reproducible output |

Writes `incident-tickets.json` to the current working directory.

### Database

```powershell
psql -U postgres -f database/001_create_pytickets.sql
psql -U postgres -d pyTickets -f database/002_add_ticket_embeddings.sql
```

Database name: **`pyTickets`**. Connection string and env vars use the `PYTICKETAGENT_*` prefix (see `.env.example`).

`002` enables `vector` (if needed) and adds dual embedding columns + HNSW indexes:

| Space | Default model | Dimensions |
|-------|---------------|------------|
| FastEmbed | `BAAI/bge-base-en-v1.5` | 768 |
| Ollama | `nomic-embed-text` | 768 |

`POST /ingest` embeds both spaces (in parallel), then upserts ticket + vectors. Per-space failures set that space to `NULL` (ticket still saved). If the embedding text hash and model are unchanged, existing vectors are preserved (see [Content hash skip](#content-hash-skip-preserve-vectors)). `GET /search` and `POST /assist` use hybrid retrieval (FTS + one semantic space, fused with RRF).

### API

Copy `.env.example` to `.env` and set `PYTICKETAGENT_DATABASE_URL` (and LLM vars for Assist), then:

```powershell
uv run uvicorn pyticketagent_api.main:app --reload --port 8000
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/ingest` | Upsert tickets (soft-fail per ticket) and dual-space embeddings (soft-fail per space) |
| `GET` | `/incidents/{id}` | Fetch one incident by id (404 if missing) |
| `GET` | `/search` | Hybrid search (FTS + semantic / RRF); optional filters and `embedding_space` |
| `GET` | `/incidents/{id}/assist` | LLM next steps + customer draft for one incident |
| `POST` | `/assist` | Hybrid search + LLM: relevant incidents, next steps, customer draft |

OpenAPI docs: `http://localhost:8000/docs`

### Configure the LLM provider

Assist uses the catalog in `packages/pyticketagent_core/src/pyticketagent_core/resources/ai_providers.json`. Set provider/model (and API key when needed), then restart the API.

```powershell
# Ollama example
$env:PYTICKETAGENT_LLM_PROVIDER = "ollama"
$env:PYTICKETAGENT_LLM_MODEL = "llama3.2:3b"

# Groq example
$env:PYTICKETAGENT_LLM_PROVIDER = "groq"
$env:PYTICKETAGENT_LLM_MODEL = "openai/gpt-oss-20b"
$env:PYTICKETAGENT_GROQ_API_KEY = "..."

# Gemini example
$env:PYTICKETAGENT_LLM_PROVIDER = "gemini"
$env:PYTICKETAGENT_LLM_MODEL = "gemini-2.5-flash"
$env:PYTICKETAGENT_GEMINI_API_KEY = "..."
```

```powershell
# Search (hybrid; omit embedding_space to use defaultSearchSpace from config)
Invoke-RestMethod "http://localhost:8000/search?q=timeout&environment=production"
Invoke-RestMethod "http://localhost:8000/search?q=timeout&embedding_space=fastembed"

# Assist by incident id
Invoke-RestMethod "http://localhost:8000/incidents/1/assist"

# Assist from a question (hybrid search + LLM)
Invoke-RestMethod "http://localhost:8000/assist" -Method Post -ContentType "application/json" -Body '{"question":"Redis timeouts in production"}'
Invoke-RestMethod "http://localhost:8000/assist" -Method Post -ContentType "application/json" -Body '{"question":"Redis timeouts in production","embedding_space":"ollama"}'
```

`GET /search` returns up to **10** full incident tickets (`count` + `results`). Returns `400` if `q` is missing or blank. Optional `embedding_space` is `fastembed` or `ollama` (invalid values → `400`).

Assist endpoints return `503` if LLM configuration is missing/invalid or the request times out, and `502` if the LLM response could not be parsed. `GET /incidents/{id}/assist` also returns `404` if the ticket does not exist. `POST /assist` returns `400` if `question` is missing or blank.

### Configure embeddings (ingest)

Edit the packaged API config:

`packages/pyticketagent_core/src/pyticketagent_core/resources/embedding_providers.json`

| JSON field | Purpose |
|------------|---------|
| `spaces.fastembed` / `spaces.ollama` | `enabled`, `providerId`, `model` for each dual-space column |
| `requestTimeoutSeconds` | Ollama embed HTTP timeout |
| `defaultSearchSpace` | Default semantic leg when `embedding_space` is omitted (`fastembed` / `ollama`) |
| `providers` | Catalog of available models (must include the active `spaces.*.model` entries) |

Restart the API after editing. For Ollama space:

```powershell
ollama pull nomic-embed-text
```

Embedding failures are logged (WARNING) only; they do not appear in the ingest JSON response.

## Environment variables

| Variable | Required for | Description |
|----------|--------------|-------------|
| `PYTICKETAGENT_DATABASE_URL` | API | PostgreSQL connection string for `pyTickets` |
| `PYTICKETAGENT_DATABASE_RETRY_MAX_ATTEMPTS` | API (optional) | Transient DB retries after first failure (default `3`) |
| `PYTICKETAGENT_DATABASE_RETRY_INITIAL_DELAY_MS` | API (optional) | Initial retry backoff in ms (default `200`) |
| `PYTICKETAGENT_DATABASE_RETRY_MAX_DELAY_MS` | API (optional) | Max retry backoff in ms (default `2000`) |
| `PYTICKETAGENT_LLM_PROVIDER` | Assist | Provider id from `ai_providers.json` |
| `PYTICKETAGENT_LLM_MODEL` | Assist | Model name for the chosen provider |
| `PYTICKETAGENT_GROQ_API_KEY` | Groq | API key when provider is `groq` |
| `PYTICKETAGENT_GEMINI_API_KEY` | Gemini | API key when provider is `gemini` |
| `PYTICKETAGENT_LLM_REQUEST_TIMEOUT_SECONDS` | Assist (optional) | LLM HTTP timeout (default `120`) |
| `PYTICKETAGENT_MAX_OUTPUT_TOKENS` | Assist (optional) | Max output tokens (default `1024`) |
| `PYTICKETAGENT_LLM_TRANSIENT_RETRY_MAX_ATTEMPTS` | Assist (optional) | Transient LLM retries after first failure (default `5`) |
| `PYTICKETAGENT_LLM_TRANSIENT_RETRY_INITIAL_DELAY_MS` | Assist (optional) | Initial LLM retry backoff in ms (default `1000`) |
| `PYTICKETAGENT_LLM_TRANSIENT_RETRY_MAX_DELAY_MS` | Assist (optional) | Max LLM retry backoff in ms (default `60000`) |

Embedding ingest settings live in `embedding_providers.json` (see above), not environment variables.

## Workspace layout

```
packages/
  pyticketagent_core/
  pyticketagent_api/
  pyticketagent_generator/
database/
tests/
```

## Embedding architecture (Phase A + B)

Dual-space POC: every ingest can store **two** 768-d vectors on the same `tickets` row (FastEmbed + Ollama). Phase B wires hybrid search: FTS + **one** embedding space per request, fused with Reciprocal Rank Fusion (RRF). Spaces are never mixed in a single cosine ranking.

### End-to-end flow

```
embedding_providers.json
        │
        ▼
main.py lifespan → EmbeddingAppConfig → DualSpaceEmbeddingRuntime
        │
POST /ingest → TicketIngestService
        │  build text + hash (per space)
        │  FastEmbed + Ollama embed (parallel; soft-fail → NULL)
        ▼
TicketRepository.upsert → PostgreSQL tickets
        (embedding_fastembed* / embedding_ollama* columns)

GET /search / POST /assist → TicketHybridSearchService
        │  FTS (ts_rank) + semantic (one space) in parallel
        │  soft-fail semantic → FTS-only
        ▼
RRF fuse → top 10 IncidentTicket results
```

### Content hash skip (preserve vectors)

The hash is **not** of the whole DB row. It is a SHA-256 of the **embedding document text** for that space (`TicketEmbeddingTextBuilder`: service, environment, tags, title, description, resolution; plus Nomic `search_document:` prefix for Ollama).

For a space, ingest **preserves** the existing vector (no re-embed) only when **all** are true:

1. A vector already exists for that space
2. Stored `embedding_*_content_hash` equals the new hash of that embed text
3. Stored `embedding_*_model` equals the current configured model id (e.g. `fastembed:BAAI/bge-base-en-v1.5`)

So: **same embed text + same model ⇒ treat embedding input as unchanged ⇒ keep vectors**.

If the embed text changes or the configured model changes, that space is re-embedded (or cleared to `NULL` on embed failure).

Fields not in the embed body (e.g. `severity`, `id`, `created_at`) do not affect the hash; changing only those will skip re-embed.

### `EmbeddingClient` (protocol, not implementation)

[`embedding_client.py`](packages/pyticketagent_core/src/pyticketagent_core/embeddings/embedding_client.py) defines a **Python `Protocol`**: a contract that any embedding backend must implement. It declares one method — `async def embed(texts) -> list[list[float]]` — and contains no logic. The `...` in the file means “signature only,” not “unfinished code.”

This matches how LLM assist uses [`chat_client.py`](packages/pyticketagent_core/src/pyticketagent_core/ai/chat_client.py) (`ChatClient` protocol vs concrete clients).

| Piece | Role |
|-------|------|
| `EmbeddingClient` | Interface ingest code depends on |
| `FastEmbedEmbeddingClient` | In-process FastEmbed (ONNX via `asyncio.to_thread`) |
| `OllamaEmbeddingClient` | Ollama HTTP embed via SDK |
| `EmbeddingClientFactory` | Creates the right client from provider kind in JSON config |
| `DualSpaceEmbeddingRuntime` | Holds both clients + bindings for the POC |

Flow: `TicketIngestService` only calls `await client.embed([text])`. It does not know FastEmbed from Ollama. At startup, `DualSpaceEmbeddingRuntimeFactory` wires the concrete clients from `embedding_providers.json`. Tests use a fake class with the same `embed` method — no inheritance required; `Protocol` is structural typing.

### Where things live

| Concern | Location |
|---------|----------|
| Schema / pgvector columns | [`database/002_add_ticket_embeddings.sql`](database/002_add_ticket_embeddings.sql) |
| Active models, enabled flags, timeout | [`embedding_providers.json`](packages/pyticketagent_core/src/pyticketagent_core/resources/embedding_providers.json) (`spaces`, `requestTimeoutSeconds`, …) |
| Config load + provider catalog types | `packages/pyticketagent_core/.../embeddings/` (`json_embedding_provider_registry_loader.py`, `embedding_app_config.py`, …) |
| FastEmbed / Ollama clients | `fastembed_embedding_client.py`, `ollama_embedding_client.py`, `embedding_client_factory.py` |
| Dual-space runtime | `dual_space_embedding_runtime.py` + `_factory.py` |
| Text to embed + content hash | `ticket_embedding_text_builder.py`, `embedding_content_hasher.py` |
| Persist vectors | [`ticket_repository.py`](packages/pyticketagent_core/src/pyticketagent_core/data/ticket_repository.py) (`upsert`, `get_embedding_meta`) |
| FTS / semantic query | [`ticket_repository.py`](packages/pyticketagent_core/src/pyticketagent_core/data/ticket_repository.py) (`search_fts`, `search_semantic`) |
| RRF fusion | [`rrf_rank_fusion.py`](packages/pyticketagent_core/src/pyticketagent_core/data/rrf_rank_fusion.py) |
| Hybrid search orchestration | [`ticket_hybrid_search_service.py`](packages/pyticketagent_api/src/pyticketagent_api/services/ticket_hybrid_search_service.py) |
| Ingest orchestration + logging | [`ticket_ingest_service.py`](packages/pyticketagent_api/src/pyticketagent_api/services/ticket_ingest_service.py) |
| App startup wiring | [`main.py`](packages/pyticketagent_api/src/pyticketagent_api/main.py), [`dependencies.py`](packages/pyticketagent_api/src/pyticketagent_api/dependencies.py) |
| Unit tests | `tests/unit/embeddings/*`, `tests/unit/api/*`, `tests/unit/data/test_rrf_rank_fusion.py` |

### `embeddings/` package (core) — by role

**Config / catalog**

- `embedding_providers_resource.py` — read packaged JSON
- `embedding_providers_file.py` — JSON document schema
- `embedding_space_binding_config.py` — one space’s enabled/provider/model
- `embedding_app_config.py` — loaded config + registry
- `embedding_space.py`, `embedding_provider_kind.py`
- `embedding_model_definition.py`, `embedding_provider_definition.py`, `embedding_model_binding.py`
- `json_embedding_provider_registry.py`, `json_embedding_provider_registry_loader.py`

**Runtime / providers**

- `embedding_client.py` — protocol
- `fastembed_embedding_client.py`, `ollama_embedding_client.py`
- `embedding_client_factory.py`
- `dual_space_embedding_runtime.py`, `dual_space_embedding_runtime_factory.py`

**Ingest helpers**

- `ticket_embedding_text_builder.py` — document text; Nomic `search_document:` / `search_query:` for Ollama
- `embedding_content_hasher.py` — skip re-embed when unchanged
- `embedding_space_write.py`, `ticket_embeddings_write.py` — preserve / clear / set per space
- `ticket_embedding_meta.py`, `ticket_embedding_space_meta.py` — DB meta for skip decisions
- `pgvector_literal.py` — vector text format for asyncpg

### Not part of embeddings

LLM assist still uses `ai_providers.json` + `PYTICKETAGENT_LLM_*` env vars under `pyticketagent_core/ai/`. Candidate retrieval for `POST /assist` shares the hybrid embedding search path; the LLM draft/rank step itself remains independent of embedding providers.
