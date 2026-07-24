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

### Database (API — later)

```powershell
psql -U postgres -f database/001_create_pytickets.sql
```

Database name: **`pyTickets`**. Connection string and env vars use the `PYTICKETAGENT_*` prefix (see `.env.example`).

### API (later)

```powershell
uv run uvicorn pyticketagent_api.main:app --reload --port 8000
```

## Environment variables

| Variable | Required for | Description |
|----------|--------------|-------------|
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
