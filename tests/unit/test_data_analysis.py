
from decimal import Decimal

from app.agents.base import AgentContext
from app.agents.data_analysis import DataAnalysisAgent


def test_analysis_reconciles_grouped_totals():
    context = AgentContext(
        request_id="analysis-001",
        raw_records=[
            {"Region": "North", "Amount": "100.25"},
            {"Region": "North", "Amount": "50.25"},
            {"Region": "South", "Amount": "200.00"},
        ],
    )

    result = DataAnalysisAgent().run(context)

    assert result.status == "success"
    assert context.verification["status"] == "verified"
    assert context.verification["checks_failed"] == 0
    assert sum(
        (row["Amount"] for row in context.calculated_data),
        Decimal(0),
    ) == Decimal("350.50")


def test_invalid_metric_does_not_pass_verification():
    context = AgentContext(
        request_id="analysis-002",
        raw_records=[
            {"Region": "North", "Amount": "100"},
            {"Region": "South", "Amount": "invalid"},
        ],
    )

    result = DataAnalysisAgent().run(context)

    assert result.status == "error"
    assert context.verification["status"] == "unverified"
    assert context.verification["checks_failed"] > 0


def test_empty_records_are_not_verified():
    context = AgentContext(
        request_id="analysis-003",
        raw_records=[],
    )

    result = DataAnalysisAgent().run(context)

    assert result.status == "error"
    assert context.verification["status"] == "unverified"
