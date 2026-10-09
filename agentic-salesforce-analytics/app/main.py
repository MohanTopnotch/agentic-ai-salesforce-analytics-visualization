from fastapi import FastAPI
from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Starter API; Salesforce and agent integrations are not yet configured.",
)
app.include_router(router, prefix=settings.api_prefix)

@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
