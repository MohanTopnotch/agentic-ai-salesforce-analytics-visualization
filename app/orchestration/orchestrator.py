from uuid import uuid4
from app.agents.base import AgentContext
from app.schemas.api import AnalyticsQueryRequest, AnalyticsQueryResponse

class AnalyticsOrchestrator:
    def run(self, request: AnalyticsQueryRequest) -> AnalyticsQueryResponse:
        request_id = str(uuid4())
        _context = AgentContext(
            request_id=request_id, session_id=request.session_id, user_id=request.user_id,
            role=request.role, question=request.question,
            conversation_history=tuple(request.conversation_history),
        )
        return AnalyticsQueryResponse(
            status="not_implemented",
            message="The API skeleton is running, but agents and Salesforce integration are not implemented yet.",
            session_id=request.session_id, audit_id=request_id,
            verification={"status": "not_run"}, lineage={"status": "not_available"},
        )
