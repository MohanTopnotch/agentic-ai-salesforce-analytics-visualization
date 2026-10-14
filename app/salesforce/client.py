
"""Common interface for mock and live Salesforce clients."""

from abc import ABC, abstractmethod
from typing import Any


class SalesforceClient(ABC):
    """Define the contract implemented by Salesforce data clients."""

    @abstractmethod
    def describe_object(self, object_name: str) -> dict[str, Any]:
        """Return metadata for a Salesforce object."""
        raise NotImplementedError

    @abstractmethod
    def query(self, soql: str) -> dict[str, Any]:
        """Execute a supported, validated SOQL query."""
        raise NotImplementedError

    @abstractmethod
    def get_accessible_objects(
        self, user_id: str | None = None
    ) -> list[str]:
        """Return Salesforce objects available to the caller."""
        raise NotImplementedError
