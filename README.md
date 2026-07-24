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
- An LLM provider for Assist endpoints (later milestone)

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

Copy `.env.example` to `.env` and set `PYTICKETAGENT_DATABASE_URL`, then:

```powershell
uv run uvicorn pyticketagent_api.main:app --reload --port 8000
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/ingest` | Upsert a JSON array of incident tickets (soft-fail per ticket) |
| `GET` | `/incidents/{id}` | Fetch one incident by id (404 if missing) |

OpenAPI docs: `http://localhost:8000/docs`

## Environment variables

| Variable | Required for | Description |
|----------|--------------|-------------|
| `PYTICKETAGENT_DATABASE_URL` | API | PostgreSQL connection string for `pyTickets` |
| `PYTICKETAGENT_DATABASE_RETRY_MAX_ATTEMPTS` | API (optional) | Transient DB retries after first failure (default `3`) |
| `PYTICKETAGENT_DATABASE_RETRY_INITIAL_DELAY_MS` | API (optional) | Initial retry backoff in ms (default `200`) |
| `PYTICKETAGENT_DATABASE_RETRY_MAX_DELAY_MS` | API (optional) | Max retry backoff in ms (default `2000`) |
| `PYTICKETAGENT_LLM_PROVIDER` | Assist | Provider id from `ai-providers.json` |
| `PYTICKETAGENT_LLM_MODEL` | Assist | Model name for the chosen provider |
| `PYTICKETAGENT_GROQ_API_KEY` | Groq | API key when provider is `groq` |
| `PYTICKETAGENT_GEMINI_API_KEY` | Gemini | API key when provider is `gemini` |

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
