from decimal import Decimal

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


def test_visualization_builds_valid_pie_and_donut_traces():
    rows = [
        {"Industry": "Technology", "AnnualRevenue": Decimal("125000.50")},
        {"Industry": "Finance", "AnnualRevenue": Decimal("75000.25")},
    ]

    for question, chart_type, hole in (
        ("Show revenue by industry as a pie chart", "pie", 0),
        ("Show revenue by industry as a circular chart", "donut", 0.5),
    ):
        context = AgentContext(
            request_id="test-pie",
            user_question=question,
            calculated_data=rows,
            verification={"status": "verified"},
        )

        result = VisualizationAgent().run(context)
        trace = result.output["visualization"]["data"][0]

        assert result.status == "success"
        assert result.output["visualization"]["chart_type"] == chart_type
        assert trace["type"] == "pie"
        assert trace["labels"] == ["Technology", "Finance"]
        assert trace["values"] == [125000.5, 75000.25]
        assert trace["hole"] == hole


def test_visualization_uses_date_dimension_for_line_chart():
    context = AgentContext(
        request_id="test-line",
        user_question="Show monthly revenue as a line chart",
        calculated_data=[
            {"CloseDate": "2026-01-01", "Revenue": Decimal("10.50")},
            {"CloseDate": "2026-02-01", "Revenue": Decimal("20.25")},
        ],
        verification={"status": "verified"},
    )

    result = VisualizationAgent().run(context)
    spec = result.output["visualization"]

    assert result.status == "success"
    assert spec["chart_type"] == "line"
    assert spec["data"][0]["type"] == "scatter"
    assert spec["data"][0]["mode"] == "lines+markers"
    assert spec["data"][0]["y"] == [10.5, 20.25]
    assert spec["layout"]["xaxis"]["type"] == "date"
