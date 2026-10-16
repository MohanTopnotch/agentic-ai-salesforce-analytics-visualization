import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


BENCHMARK_QUERIES = [
    "Show total sales by region.",
    "Who are the top 10 sales representatives?",
    "Show monthly revenue for 2026.",
    "Compare this year's revenue with last year's.",
    "Show opportunity pipeline by stage.",
    "Which opportunities are likely to close this month?",
    "Show opportunities above $100K.",
    "Show the top 20 customers by revenue.",
    "Which customers haven't purchased in the last 6 months?",
    "Show lead conversion rate by source.",
]


@pytest.mark.parametrize("question", BENCHMARK_QUERIES)
def test_analytics_query_pipeline(question: str):
    response = client.post(
        "/api/v1/query",
        json={
            "question": question,
            "user_id": "integration-test-user",
        },
    )

    assert response.status_code == 200, (
        f"Question: {question}\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )

    body = response.json()

    assert body["request_id"]
    assert body["status"] == "success"
    assert body["state"] == "completed"
    assert isinstance(body["data"], dict)
    assert body["verified"] is True


def test_query_endpoint_rejects_empty_question():
    response = client.post(
        "/api/v1/query",
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_query_endpoint_rejects_missing_question():
    response = client.post(
        "/api/v1/query",
        json={"user_id": "integration-test-user"},
    )

    assert response.status_code == 422
