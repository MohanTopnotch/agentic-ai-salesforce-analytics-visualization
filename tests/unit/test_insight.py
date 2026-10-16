from app.agents.base import AgentContext
from app.agents.insight import InsightAgent


def test_insight_requires_verification():
    agent = InsightAgent()

    context = AgentContext(
        request_id="test-1",
        verification={"status": "unverified"},
    )

    result = agent.run(context)

    assert result.status == "error"
