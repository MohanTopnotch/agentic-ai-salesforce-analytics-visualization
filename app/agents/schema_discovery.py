from app.agents.base import AgentContext, AgentResult, BaseAgent

class SchemaDiscoveryAgent(BaseAgent):
    name = "schema_discovery"
    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(False, errors=[{"code": "NOT_IMPLEMENTED", "message": "Metadata discovery is not implemented."}])
