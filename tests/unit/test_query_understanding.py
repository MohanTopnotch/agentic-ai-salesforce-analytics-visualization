from app.agents.base import AgentContext
from app.agents.query_understanding import QueryUnderstandingAgent


def test_detect_sales_by_region():
    agent = QueryUnderstandingAgent()

    context = AgentContext(
        request_id="test-1",
        user_question="Show total sales by region",
    )

    result = agent.run(context)

    assert result.status == "success"
    assert result.output["intent"]["intent"] == "sales_by_region"
