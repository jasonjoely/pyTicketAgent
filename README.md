# pyTicketAgent

Python equivalent of [DFAgent](../DFAgent): incident ticket management with PostgreSQL full-text search and LLM-assisted troubleshooting.

| Package | Purpose |
|---------|---------|
| `pyticketagent_core` | Shared models, data access (asyncpg), AI helpers |
| `pyticketagent_api` | FastAPI REST API (Ingest, Search, Assist) |
| `pyticketagent_generator` | CLI that generates sample incident ticket JSON |

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 12+ (for API; not required for Generator)
- An LLM provider for Assist endpoints ([Ollama](https://ollama.com/), [Groq](https://groq.com/), or [Google Gemini](https://ai.google.dev/))

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
```

Database name: **`pyTickets`**. Connection string and env vars use the `PYTICKETAGENT_*` prefix (see `.env.example`).

### API

Copy `.env.example` to `.env` and set `PYTICKETAGENT_DATABASE_URL` (and LLM vars for Assist), then:

```powershell
uv run uvicorn pyticketagent_api.main:app --reload --port 8000
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/ingest` | Upsert a JSON array of incident tickets (soft-fail per ticket) |
| `GET` | `/incidents/{id}` | Fetch one incident by id (404 if missing) |
| `GET` | `/search` | Full-text search with optional environment/service/severity/tags filters |
| `GET` | `/incidents/{id}/assist` | LLM next steps + customer draft for one incident |
| `POST` | `/assist` | Search + LLM: relevant incidents, next steps, customer draft |

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
# Search
Invoke-RestMethod "http://localhost:8000/search?q=timeout&environment=production"

# Assist by incident id
Invoke-RestMethod "http://localhost:8000/incidents/1/assist"

# Assist from a question (search + LLM)
Invoke-RestMethod "http://localhost:8000/assist" -Method Post -ContentType "application/json" -Body '{"question":"Redis timeouts in production"}'
```

`GET /search` returns `400` if `q` is missing or blank.

Assist endpoints return `503` if LLM configuration is missing/invalid or the request times out, and `502` if the LLM response could not be parsed. `GET /incidents/{id}/assist` also returns `404` if the ticket does not exist. `POST /assist` returns `400` if `question` is missing or blank.

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

## Workspace layout

```
packages/
  pyticketagent_core/
  pyticketagent_api/
  pyticketagent_generator/
database/
tests/
```

## Relationship to DFAgent

Starting artifacts (DDL, ticket scenarios, AI provider config, prompts) were copied from DFAgent and adapted for this repo. The stacks are independent; this database is **`pyTickets`**, not `dftickets`.
