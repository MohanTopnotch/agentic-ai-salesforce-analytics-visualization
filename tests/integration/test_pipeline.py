import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


BENCHMARK_QUERIES = [
    "Show total sales by region.",
    "Show monthly revenue for 2026.",
    "Show opportunity pipeline by stage.",
    "Show revenue by industry.",
    "Show revenue by lead source.",
]


@pytest.mark.parametrize("question", BENCHMARK_QUERIES)
def test_supported_analytics_query_pipeline(question: str):
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


UNSUPPORTED_QUERIES = [
    "Who are the top 10 sales representatives?",
    "Compare this year's revenue with last year's.",
    "Which opportunities are likely to close this month?",
    "Show opportunities above $100K.",
    "Show the top 20 customers by revenue.",
    "Which customers haven't purchased in the last 6 months?",
    "Show lead conversion rate by source.",
    "Hello, what is the weather today?",
]


@pytest.mark.parametrize("question", UNSUPPORTED_QUERIES)
def test_unsupported_or_ambiguous_queries_do_not_execute(question: str):
    response = client.post(
        "/api/v1/query",
        json={
            "question": question,
            "user_id": "integration-test-user",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["verified"] is False
    assert body["state"] == "clarification_required"
    assert "clarification_question" in body
    assert "query_plan" not in body["data"]


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


def test_sales_by_region_returns_opportunity_amounts_by_region():
    response = client.post(
        "/api/v1/query",
        json={
            "question": "Show total sales by region",
            "user_id": "integration-test-user",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["verified"] is True
    assert body["data"]["query_plan"]["object_name"] == "Opportunity"
    assert body["data"]["query_plan"]["fields"] == ["Amount", "Region"]
    assert {
        row["Region"]: float(row["Amount"])
        for row in body["data"]["calculated_data"]
    } == {
        "North": 150000,
        "South": 100000,
    }
    assert "StageName = 'Closed Won'" in body["data"]["query_plan"]["soql_query"]
    assert body["data"]["visualization"]["layout"]["title"]["text"] == (
        "Sales Amount by Region"
    )
    assert body["data"]["visualization"]["data"][0]["y"] == [
        150000.0,
        100000.0,
    ]


def test_monthly_revenue_filters_to_requested_year_and_sorts_months():
    response = client.post(
        "/api/v1/query",
        json={
            "question": "Show monthly revenue for 2026",
            "user_id": "integration-test-user",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["verified"] is True
    assert "CloseDate >= '2026-01-01'" in body["data"]["query_plan"]["soql_query"]
    assert "CloseDate <= '2026-12-31'" in body["data"]["query_plan"]["soql_query"]
    assert "StageName = 'Closed Won'" in body["data"]["query_plan"]["soql_query"]
    assert body["data"]["visualization"]["chart_type"] == "line"
    assert [row["Month"] for row in body["data"]["calculated_data"]] == [
        "2026-02-01",
        "2026-03-01",
    ]
