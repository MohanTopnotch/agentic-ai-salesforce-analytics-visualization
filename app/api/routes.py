from fastapi import APIRouter, HTTPException
from app.schemas.api import AnalyticsQueryRequest, AnalyticsQueryResponse, HealthResponse
from app.orchestration.orchestrator import AnalyticsOrchestrator

router = APIRouter()
orchestrator = AnalyticsOrchestrator()

@router.get("/health", response_model=HealthResponse, tags=["health"])
def api_health() -> HealthResponse:
    return HealthResponse(status="ok")

@router.post("/analytics/query", response_model=AnalyticsQueryResponse, tags=["analytics"])
def run_analytics(request: AnalyticsQueryRequest) -> AnalyticsQueryResponse:
    try:
        return orchestrator.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
