import pytest

from app.mock_salesforce_client import MockSalesforceClient
from app.orchestration.orchestrator import (
    AnalyticsOrchestrator,
    WorkflowErrorCode,
    WorkflowState,
)


def test_create_request_context():
    orchestrator = AnalyticsOrchestrator()

    context = orchestrator._create_context(
        "Show total sales by region",
        user_id="test-user",
    )

    assert context.request_id
    assert context.user_request == "Show total sales by region"
    assert context.user_id == "test-user"
    assert context.state == WorkflowState.CONTEXT_CREATED
    assert context.repair_attempts == 0


def test_empty_request_is_rejected():
    orchestrator = AnalyticsOrchestrator()

    with pytest.raises(ValueError, match="non-empty string"):
        orchestrator._create_context("   ")


def test_invalid_request_type_is_rejected():
    orchestrator = AnalyticsOrchestrator()

    with pytest.raises(ValueError, match="non-empty string"):
        orchestrator._create_context(None)


def test_repair_attempt_limit_is_enforced():
    with pytest.raises(ValueError):
        AnalyticsOrchestrator(max_repair_attempts=4)

    assert AnalyticsOrchestrator(max_repair_attempts=3).max_repair_attempts == 3


def test_missing_agent_returns_structured_error():
    orchestrator = AnalyticsOrchestrator(agents={})

    response = orchestrator.run("Show sales by region")

    assert response.status == "error"
    assert response.state == WorkflowState.FAILED
    assert response.error_code == WorkflowErrorCode.INTERNAL_ERROR


def test_injected_salesforce_client_is_used_for_metadata_and_queries():
    class TrackingSalesforceClient(MockSalesforceClient):
        def __init__(self):
            super().__init__()
            self.metadata_reads = 0
            self.query_reads = 0

        def get_accessible_objects(self, user_id=None):
            self.metadata_reads += 1
            return super().get_accessible_objects(user_id)

        def query(self, soql):
            self.query_reads += 1
            return super().query(soql)

    client = TrackingSalesforceClient()
    orchestrator = AnalyticsOrchestrator(salesforce_client=client)

    response = orchestrator.run("Show revenue by industry")

    assert response.status == "success"
    assert response.data["lineage"]["source"] == "TrackingSalesforceClient"
    assert response.data["intent"]["metrics"] == ["AnnualRevenue"]
    assert response.data["intent"]["group_by"] == ["Industry"]
    assert (
        response.data["visualization"]["layout"]["title"]["text"]
        == "Annual Revenue by Industry"
    )
    assert client.metadata_reads == 1
    assert client.query_reads == 1


def test_orchestrator_respects_requested_donut_chart():
    response = AnalyticsOrchestrator().run(
        "Show revenue by industry as a circular chart"
    )

    assert response.status == "success"
    assert response.data["visualization"]["chart_type"] == "donut"
    assert response.data["visualization"]["data"][0]["type"] == "pie"
    assert response.data["visualization"]["data"][0]["hole"] == 0.5
