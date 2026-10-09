from abc import ABC, abstractmethod
from typing import Any

class SalesforceClient(ABC):
    """Read-only Salesforce adapter contract; OAuth and REST implementation are pending."""
    @abstractmethod
    def describe_object(self, object_name: str) -> dict[str, Any]:
        raise NotImplementedError
    @abstractmethod
    def query(self, soql: str) -> list[dict[str, Any]]:
        raise NotImplementedError
    @abstractmethod
    def get_accessible_objects(self, user_id: str | None = None) -> list[str]:
        raise NotImplementedError
