import pytest

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

    assert AnalyticsOrchestrator(
        max_repair_attempts=3
    ).max_repair_attempts == 3

def test_missing_agent_returns_structured_error():
    orchestrator = AnalyticsOrchestrator(agents={})

    response = orchestrator.run("Show sales by region")

    assert response.status == "error"
    assert response.state == WorkflowState.FAILED
    assert response.error_code == WorkflowErrorCode.INTERNAL_ERROR