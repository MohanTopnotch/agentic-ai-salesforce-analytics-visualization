
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language question about Salesforce data.",
    )
    user_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Authenticated application user identifier.",
    )


class AnalyticsQueryResponse(BaseModel):
    request_id: str
    status: str
    state: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None
    clarification_question: str | None = None
    verified: bool = False