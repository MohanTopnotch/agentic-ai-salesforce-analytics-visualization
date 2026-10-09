from app.agents.base import AgentContext, AgentResult, BaseAgent

class DataAnalysisAuditorAgent(BaseAgent):
    name = "data_analysis_auditor"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, errors=[{"code": "NOT_IMPLEMENTED", "message": "Analysis and verification are not implemented."}])
