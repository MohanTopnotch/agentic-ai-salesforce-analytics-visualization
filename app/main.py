from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import get_orchestrator
from app.api.routes import router as analytics_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_orchestrator()
    yield


app = FastAPI(
    title="Agentic Salesforce Analytics API",
    version="1.0.0",
    description=(
        "Natural-language Salesforce analytics, "
        "query execution, verification, and visualization."
    ),
    lifespan=lifespan,
)

app.include_router(
    analytics_router,
    prefix="/api/v1",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
