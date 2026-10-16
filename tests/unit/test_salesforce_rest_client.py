import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.salesforce.factory import create_salesforce_client
from app.salesforce.rest_client import SalesforceAPIError, SalesforceRESTClient


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.payload


def test_live_client_authenticates_describes_and_follows_query_pages(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request)
        url = request.full_url
        if url.endswith("/services/oauth2/token"):
            form = parse_qs(request.data.decode("utf-8"))
            assert form["grant_type"] == ["client_credentials"]
            assert form["client_id"] == ["client-id"]
            assert form["client_secret"] == ["client-secret"]
            return FakeResponse(
                {
                    "access_token": "access-token",
                    "instance_url": "https://example.my.salesforce.com",
                }
            )
        assert request.get_header("Authorization") == "Bearer access-token"
        if url.endswith("/services/data/v66.0/sobjects"):
            return FakeResponse(
                {
                    "sobjects": [
                        {"name": "Lead", "queryable": True},
                        {"name": "Task", "queryable": False},
                    ]
                }
            )
        if url.endswith("/services/data/v66.0/sobjects/Lead/describe"):
            return FakeResponse(
                {
                    "name": "Lead",
                    "fields": [{"name": "AnnualRevenue"}, {"name": "Industry"}],
                }
            )
        if "/services/data/v66.0/query?" in url:
            query = parse_qs(urlparse(url).query)["q"][0]
            assert query == "SELECT AnnualRevenue, Industry FROM Lead LIMIT 10"
            return FakeResponse(
                {
                    "totalSize": 2,
                    "done": False,
                    "nextRecordsUrl": "/services/data/v66.0/query/next-page",
                    "records": [
                        {
                            "attributes": {"type": "Lead"},
                            "AnnualRevenue": 100,
                            "Industry": "Technology",
                        }
                    ],
                }
            )
        if url.endswith("/services/data/v66.0/query/next-page"):
            return FakeResponse(
                {
                    "totalSize": 2,
                    "done": True,
                    "records": [{"AnnualRevenue": 200, "Industry": "Finance"}],
                }
            )
        raise AssertionError(f"Unexpected request: {url}")

    monkeypatch.setattr("app.salesforce.rest_client.urlopen", fake_urlopen)
    client = SalesforceRESTClient(
        client_id="client-id",
        client_secret="client-secret",
    )

    assert client.get_accessible_objects() == ["Lead"]
    assert client.describe_object("Lead")["field_names"] == [
        "AnnualRevenue",
        "Industry",
    ]
    result = client.query("SELECT AnnualRevenue, Industry FROM Lead LIMIT 10")
    assert result == {
        "totalSize": 2,
        "records": [
            {"AnnualRevenue": 100, "Industry": "Technology"},
            {"AnnualRevenue": 200, "Industry": "Finance"},
        ],
    }
    assert len(calls) == 5


def test_query_rejects_external_pagination_urls(monkeypatch):
    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/services/oauth2/token"):
            return FakeResponse(
                {
                    "access_token": "access-token",
                    "instance_url": "https://example.my.salesforce.com",
                }
            )
        return FakeResponse(
            {
                "totalSize": 2,
                "done": False,
                "nextRecordsUrl": "https://attacker.example/collect",
                "records": [],
            }
        )

    monkeypatch.setattr("app.salesforce.rest_client.urlopen", fake_urlopen)
    client = SalesforceRESTClient(
        client_id="client-id",
        client_secret="client-secret",
    )

    with pytest.raises(SalesforceAPIError, match="pagination URL"):
        client.query("SELECT Id FROM Lead LIMIT 10")


def test_live_mode_requires_oauth_configuration(monkeypatch):
    monkeypatch.setenv("SALESFORCE_MODE", "live")
    monkeypatch.delenv("SALESFORCE_CLIENT_ID", raising=False)
    monkeypatch.delenv("SALESFORCE_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="SALESFORCE_CLIENT_ID"):
        create_salesforce_client()


def test_live_mode_builds_configured_rest_client(monkeypatch):
    monkeypatch.setenv("SALESFORCE_MODE", "live")
    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "client-id")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SALESFORCE_LOGIN_URL", "https://test.salesforce.com")

    client = create_salesforce_client()

    assert isinstance(client, SalesforceRESTClient)
    assert client.login_url == "https://test.salesforce.com"


def test_factory_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("SALESFORCE_MODE", "unknown")

    with pytest.raises(ValueError, match="SALESFORCE_MODE"):
        create_salesforce_client()
