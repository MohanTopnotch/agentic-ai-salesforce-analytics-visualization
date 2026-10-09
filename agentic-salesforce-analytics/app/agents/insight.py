from app.agents.base import AgentContext, AgentResult, BaseAgent

class InsightDiagnosticAgent(BaseAgent):
    name = "insight_diagnostic"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, errors=[{"code": "NOT_IMPLEMENTED", "message": "Insight generation is not implemented."}])
