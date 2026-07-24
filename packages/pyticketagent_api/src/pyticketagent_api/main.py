"""pyTicketAgent FastAPI application (stub — endpoints in a later milestone)."""

from fastapi import FastAPI

app = FastAPI(
    title="pyTicketAgent",
    version="0.1.0",
    description="Incident ticket API with search and LLM assist.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
