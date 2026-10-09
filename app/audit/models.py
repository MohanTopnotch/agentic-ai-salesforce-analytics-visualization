from datetime import datetime, timezone
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    audit_id: str
    request_id: str
    user_id: str | None = None
    session_id: str | None = None
    question: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    objects_used: list[str] = Field(default_factory=list)
    fields_used: list[str] = Field(default_factory=list)
    soql_hash: str | None = None
    result_count: int | None = None
    verification_status: str = "not_run"
    error_codes: list[str] = Field(default_factory=list)
