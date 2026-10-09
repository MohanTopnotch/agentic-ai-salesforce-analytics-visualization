from typing import Any
from pydantic import BaseModel, Field

class AnalyticsQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    session_id: str | None = None
    user_id: str | None = None
    role: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)

class AnalyticsQueryResponse(BaseModel):
    status: str
    message: str
    session_id: str | None = None
    intent: dict[str, Any] | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    visualization: dict[str, Any] | None = None
    insights: list[str] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, Any] = Field(default_factory=dict)
    audit_id: str | None = None

class HealthResponse(BaseModel):
    status: str
