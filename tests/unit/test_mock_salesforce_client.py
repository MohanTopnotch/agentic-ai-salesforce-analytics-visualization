import pytest

from app.mock_salesforce_client import (
    MockSalesforceClient,
    SalesforceQueryError,
)


@pytest.fixture
def client():
    return MockSalesforceClient()


def test_load_sample_records(client):
    result = client.query("SELECT Id FROM Lead")

    assert result["totalSize"] == 5
    assert result["records"][0]["Id"] == "00Q0001"


def test_describe_object(client):
    metadata = client.describe_object("Lead")

    assert metadata["name"] == "Lead"
    assert "AnnualRevenue" in metadata["field_names"]
    assert "Email" in metadata["field_names"]


def test_accessible_objects(client):
    assert client.get_accessible_objects() == ["Lead", "Opportunity"]


def test_filter_by_rating(client):
    result = client.query("SELECT Id, Rating FROM Lead WHERE Rating IN ('Hot', 'Warm')")

    assert result["totalSize"] == 4
    assert all(row["Rating"] in ("Hot", "Warm") for row in result["records"])


def test_filter_by_annual_revenue(client):
    result = client.query(
        "SELECT Id, AnnualRevenue FROM Lead WHERE AnnualRevenue > 5000000"
    )

    assert result["totalSize"] == 3
    assert {row["AnnualRevenue"] for row in result["records"]} == {
        6_000_000,
        8_000_000,
        12_000_000,
    }


def test_group_and_aggregate(client):
    result = client.query(
        "SELECT LeadSource, COUNT(Id) AS lead_count, "
        "SUM(AnnualRevenue) AS revenue "
        "FROM Lead GROUP BY LeadSource ORDER BY LeadSource ASC"
    )

    assert result["totalSize"] == 3
    assert result["records"] == [
        {"LeadSource": "Partner", "lead_count": 1, "revenue": 12_000_000},
        {"LeadSource": "Referral", "lead_count": 1, "revenue": 6_000_000},
        {"LeadSource": "Web", "lead_count": 3, "revenue": 13_000_000},
    ]


def test_limit(client):
    result = client.query("SELECT Id FROM Lead LIMIT 2")

    assert result["totalSize"] == 2
    assert len(result["records"]) == 2


def test_unknown_object_returns_structured_error(client):
    with pytest.raises(SalesforceQueryError) as exc:
        client.query("SELECT Id FROM Account")

    assert exc.value.code == "UNKNOWN_OBJECT"
    assert exc.value.to_dict()["error"]["details"]["object"] == "Account"


def test_unknown_field_returns_structured_error(client):
    with pytest.raises(SalesforceQueryError) as exc:
        client.query("SELECT InvalidField FROM Lead")

    assert exc.value.code == "UNKNOWN_FIELD"


def test_unsupported_query_is_rejected(client):
    with pytest.raises(SalesforceQueryError) as exc:
        client.query("DELETE FROM Lead")

    assert exc.value.code == "UNSUPPORTED_QUERY"


def test_subquery_is_rejected(client):
    with pytest.raises(SalesforceQueryError):
        client.query("SELECT Id, (SELECT Id FROM Contacts) FROM Lead")


def test_invalid_metadata_object(client):
    with pytest.raises(SalesforceQueryError) as exc:
        client.describe_object("UnsupportedObject")

    assert exc.value.code == "UNKNOWN_OBJECT"
