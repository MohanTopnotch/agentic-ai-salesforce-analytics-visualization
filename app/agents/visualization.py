from app.agents.base import AgentContext, AgentResult, BaseAgent

class VisualizationAgent(BaseAgent):
    name = "visualization"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, errors=[{"code": "NOT_IMPLEMENTED", "message": "Chart selection is not implemented."}])
