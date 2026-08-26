"""pyTicketAgent FastAPI application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI

from pyticketagent_core.ai.json_ai_provider_registry_loader import (
    JsonAiProviderRegistryLoader,
)
from pyticketagent_core.configuration.settings import Settings
from pyticketagent_core.data.database_pool import close_pool, create_pool
from pyticketagent_core.embeddings.dual_space_embedding_runtime_factory import (
    DualSpaceEmbeddingRuntimeFactory,
)
from pyticketagent_core.embeddings.json_embedding_provider_registry_loader import (
    JsonEmbeddingProviderRegistryLoader,
)
from pyticketagent_core.observability.logging_config import configure_logging

from pyticketagent_api.middleware.request_id_middleware import RequestIdMiddleware
from pyticketagent_api.routes import assist, ingest, incidents, search

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_format, settings.log_file)
    pool = await create_pool(settings.database_url)
    registry = JsonAiProviderRegistryLoader().load_default()
    try:
        embedding_app_config = JsonEmbeddingProviderRegistryLoader().load_default()
        embedding_runtime = DualSpaceEmbeddingRuntimeFactory(
            embedding_app_config
        ).create()
    except Exception:
        logger.error(
            "Embedding runtime failed to initialize; "
            "ingest will preserve existing embeddings and skip new embeds",
            exc_info=True,
        )
        embedding_app_config = None
        embedding_runtime = None

    app.state.settings = settings
    app.state.pool = pool
    app.state.ai_provider_registry = registry
    app.state.embedding_app_config = embedding_app_config
    app.state.embedding_runtime = embedding_runtime
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

app.add_middleware(RequestIdMiddleware)

app.include_router(ingest.router)
app.include_router(incidents.router)
app.include_router(search.router)
app.include_router(assist.router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
