from app.agents.base import AgentContext, AgentResult, BaseAgent

class QueryUnderstandingAgent(BaseAgent):
    name = "query_understanding"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, {"question": context.question},
            [{"code": "NOT_IMPLEMENTED", "message": "Intent extraction is not implemented."}])
