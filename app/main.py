
from fastapi import FastAPI

from app.api.routes import router as analytics_router

app = FastAPI(
    title="Agentic Salesforce Analytics API",
    version="1.0.0",
    description=(
        "Natural-language Salesforce analytics, "
        "query execution, verification, and visualization."
    ),
)

app.include_router(
    analytics_router,
    prefix="/api/v1",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}