from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_query_endpoint_is_honest_placeholder():
    response = client.post("/api/v1/analytics/query", json={"question": "Show total sales by region."})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_implemented"
    assert body["verification"]["status"] == "not_run"
    assert body["data"] == []
