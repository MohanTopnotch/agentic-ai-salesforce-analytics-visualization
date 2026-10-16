from dataclasses import asdict
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
)
from app.orchestration.orchestrator import AnalyticsOrchestrator
from app.salesforce.factory import create_salesforce_client

router = APIRouter(tags=["Analytics"])


@lru_cache(maxsize=1)
def get_orchestrator() -> AnalyticsOrchestrator:
    """Return the orchestrator configured with the selected Salesforce client."""
    return AnalyticsOrchestrator(salesforce_client=create_salesforce_client())


@router.post(
    "/query",
    response_model=AnalyticsQueryResponse,
    summary="Execute a Salesforce analytics query",
)
def execute_analytics_query(
    request: AnalyticsQueryRequest,
    orchestrator: AnalyticsOrchestrator = Depends(get_orchestrator),
) -> AnalyticsQueryResponse:
    try:
        result = orchestrator.run(
            request.question,
            user_id=request.user_id,
        )

        # OrchestrationResponse is a dataclass in the current design.
        if hasattr(result, "__dataclass_fields__"):
            payload = asdict(result)
        else:
            payload = result

        return AnalyticsQueryResponse.model_validate(payload)

    except Exception as exc:
        # Keep internal exception details out of the public API response.
        # Replace this with your project's structured error logger.
        raise HTTPException(
            status_code=500,
            detail="An unexpected analytics service error occurred.",
        ) from exc
