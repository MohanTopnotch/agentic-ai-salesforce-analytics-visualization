
from typing import Any

from pydantic import BaseModel, Field, field_validator


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
    )
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value

    @field_validator("session_id")
    @classmethod
    def session_id_must_not_be_blank(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Session ID must not be blank.")
        return value


class AnalyticsQueryResponse(BaseModel):
    request_id: str
    status: str
    state: str
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None
    clarification_question: str | None = None
    verified: bool = False
