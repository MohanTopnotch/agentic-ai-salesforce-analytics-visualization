from typing import Any
from app.salesforce.client import SalesforceClient

class MockSalesforceClient(SalesforceClient):
    def describe_object(self, object_name: str) -> dict[str, Any]:
        metadata = {
            "Opportunity": {"fields": {"Id": "id", "Name": "string", "Amount": "currency",
                "StageName": "picklist", "CloseDate": "date", "Region__c": "string", "OwnerId": "reference"}},
            "Lead": {"fields": {"Id": "id", "Company": "string", "Status": "picklist",
                "LeadSource": "picklist", "Industry": "picklist", "Email": "email"}},
        }
        if object_name not in metadata:
            raise ValueError(f"Object not present in mock schema: {object_name}")
        return metadata[object_name]
    def query(self, soql: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Mock query execution is not implemented yet.")
    def get_accessible_objects(self, user_id: str | None = None) -> list[str]:
        return ["Opportunity", "Lead"]
