import pytest
from app.security.soql_guard import UnsafeSOQL, validate_read_only_soql

def test_allows_basic_select():
    assert validate_read_only_soql("SELECT Id FROM Opportunity") == "SELECT Id FROM Opportunity"

@pytest.mark.parametrize("query", ["", "DELETE FROM Opportunity",
    "SELECT Id FROM Opportunity; DELETE FROM Account", "UPDATE Opportunity SET Name = 'x'"])
def test_rejects_unsafe_queries(query):
    with pytest.raises(UnsafeSOQL):
        validate_read_only_soql(query)
