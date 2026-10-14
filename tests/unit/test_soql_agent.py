from app.agents.base import AgentContext
from app.agents.soql_agent import SOQLGenerationAgent
from app.mock_salesforce_client import MockSalesforceClient
from app.security.soql_guard import SOQLSafetyGuard


def test_soql_agent_generates_validated_query():
    client = MockSalesforceClient()
    agent = SOQLGenerationAgent(
        salesforce_client=client,
        safety_guard=SOQLSafetyGuard(),
    )

    context = AgentContext(
        request_id="test-soql-001",
        user_id="dev-user",
        user_question="Show hot leads",
        intent={
            "object_name": "Lead",
            "fields": ["Company", "Rating"],
            "filters": [
                {
                    "field": "Rating",
                    "operator": "=",
                    "value": "Hot",
                }
            ],
            "limit": 10,
        },
    )

    result = agent.run(context)

    assert result.status == "success"
    assert result.validation_status == "passed"
    assert context.soql_query is not None
    assert context.soql_query.startswith("SELECT Company, Rating FROM Lead")
    assert all(row.get("Rating") == "Hot" for row in context.raw_records)
