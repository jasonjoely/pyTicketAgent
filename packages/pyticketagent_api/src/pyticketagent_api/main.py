"""pyTicketAgent FastAPI application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from pyticketagent_core.ai.json_ai_provider_registry_loader import (
    JsonAiProviderRegistryLoader,
)
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.database_pool import close_pool, create_pool

from pyticketagent_api.routes import assist, ingest, incidents, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    pool = await create_pool(settings.database_url)
    registry = JsonAiProviderRegistryLoader().load_default()
    app.state.settings = settings
    app.state.pool = pool
    app.state.ai_provider_registry = registry
    try:
        yield
    finally:
        await close_pool(pool)


app = FastAPI(
    title="pyTicketAgent",
    version="0.1.0",
    description="Incident ticket API with search and LLM assist.",
    lifespan=lifespan,
)

app.include_router(ingest.router)
app.include_router(incidents.router)
app.include_router(search.router)
app.include_router(assist.router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
