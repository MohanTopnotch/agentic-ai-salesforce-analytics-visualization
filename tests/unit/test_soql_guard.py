
import pytest

from app.security.soql_guard import SOQLSafetyGuard


@pytest.fixture
def guard():
    return SOQLSafetyGuard()


@pytest.fixture
def objects():
    return {"Account"}


@pytest.fixture
def fields():
    return {
        "Account": {
            "Id",
            "Name",
            "Industry",
            "AnnualRevenue",
        }
    }


def test_allows_permitted_select(guard, objects, fields):
    query = "SELECT Id, Name FROM Account"

    assert guard.validate_query(
        query, "user-1", objects, fields
    ) == query


def test_allows_group_by_and_aggregate(guard, objects, fields):
    query = (
        "SELECT Industry, SUM(AnnualRevenue) AS TotalRevenue "
        "FROM Account GROUP BY Industry"
    )

    assert guard.validate_query(
        query, "user-1", objects, fields
    ) == query


def test_allows_and_or_conditions(guard, objects, fields):
    query = (
        "SELECT Id, Name FROM Account "
        "WHERE Industry = 'Technology' OR Industry = 'Finance'"
    )

    assert guard.validate_query(
        query, "user-1", objects, fields
    ) == query


def test_denies_empty_object_permissions(guard, fields):
    with pytest.raises((ValueError, PermissionError)):
        guard.validate_query(
            "SELECT Id FROM Account", "user-1", set(), fields
        )


def test_denies_unauthorized_field(guard, objects, fields):
    with pytest.raises((ValueError, PermissionError)):
        guard.validate_query(
            "SELECT SecretField FROM Account",
            "user-1",
            objects,
            fields,
        )


def test_denies_unauthorized_object(guard, objects, fields):
    with pytest.raises((ValueError, PermissionError)):
        guard.validate_query(
            "SELECT Id FROM Contact",
            "user-1",
            objects,
            fields,
        )


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM Account",
        "SELECT Id FROM Account; SELECT Id FROM Account",
        "SELECT Id FROM Account -- comment",
        "SELECT Id FROM Account /* comment */",
        "SELECT Id FROM Account WHERE SecretField = 'x'",
        "SELECT Id FROM Account LIMIT 0",
        "",
    ],
)
def test_rejects_unsafe_queries(guard, objects, fields, query):
    with pytest.raises((ValueError, PermissionError)):
        guard.validate_query(query, "user-1", objects, fields)


def test_rejects_missing_user(guard, objects, fields):
    with pytest.raises(PermissionError):
        guard.validate_query(
            "SELECT Id FROM Account", "", objects, fields
        )
