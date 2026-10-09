from app.agents.base import AgentContext, AgentResult, BaseAgent

class SOQLGenerationExecutionAgent(BaseAgent):
    name = "soql_generation_execution"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, errors=[{"code": "NOT_IMPLEMENTED", "message": "SOQL generation/execution is not implemented."}])
