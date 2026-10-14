from app.agents.base import AgentContext
from app.agents.visualization import VisualizationAgent


def test_visualization_generates_bar_chart():
    context = AgentContext(
        request_id="test-001",
        user_question="Show sales by region",
        calculated_data=[
            {"Region": "North", "Amount": 150000.0},
            {"Region": "South", "Amount": 125000.0},
        ],
        verification={
            "status": "verified",
            "checks_passed": 2,
            "checks_failed": 0,
            "reconciliation_delta": 0.0,
        },
    )

    result = VisualizationAgent().run(context)

    assert result.status == "success"
    assert result.output["visualization"]["chart_type"] == "bar"
    assert context.visualization is not None
    assert context.visualization["data"][0]["x"] == [
        "North",
        "South",
    ]
