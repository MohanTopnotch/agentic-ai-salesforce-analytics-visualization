
#app/mcp/tools.py
"""Security-aware MCP tools for Salesforce analytics."""

from time import perf_counter
from typing import Any
from uuid import uuid4

from app.audit.audit_logger import AuditLogger
from app.salesforce.client import SalesforceClient
from app.security.soql_guard import SOQLSafetyGuard


class SalesforceMCPToolProvider:
    """Expose Salesforce operations through guarded MCP tools."""

    def __init__(
        self,
        client: SalesforceClient,
        safety_guard: SOQLSafetyGuard | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.client = client
        self.safety_guard = safety_guard or SOQLSafetyGuard()
        self.audit_logger = audit_logger or AuditLogger()

    def describe_object(
        self,
        object_name: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Describe an object only when the caller can access it."""
        if not user_id or not user_id.strip():
            raise PermissionError("A user identity is required.")

        accessible_objects = set(
            self.client.get_accessible_objects(user_id)
        )
        self.safety_guard.validate_object_access(
            object_name,
            accessible_objects,
        )

        return self.client.describe_object(object_name)

    def execute_soql(
        self,
        soql: str,
        *,
        user_id: str,
        accessible_objects: set[str],
        accessible_fields: dict[str, set[str]],
    ) -> dict[str, Any]:
        """Validate permissions and SOQL before executing the query."""
        request_id = str(uuid4())
        started = perf_counter()

        try:
            if not user_id or not user_id.strip():
                raise PermissionError("A user identity is required.")

            # Intersect supplied permissions with the client's object access.
            client_objects = {
                name.casefold()
                for name in self.client.get_accessible_objects(user_id)
            }
            permitted_objects = {
                name
                for name in accessible_objects
                if name.casefold() in client_objects
            }

            validated_soql = self.safety_guard.validate_query(
                soql=soql,
                user_id=user_id,
                accessible_objects=permitted_objects,
                accessible_fields=accessible_fields,
            )

            result = self.client.query(validated_soql)

            if not isinstance(result, dict):
                raise TypeError(
                    "Salesforce client returned an invalid response."
                )

            self.audit_logger.log_run(
                request_id=request_id,
                duration_ms=(perf_counter() - started) * 1000,
                state="success",
                verification_status="pending",
                lineage={
                    "source": "SalesforceMCP",
                    "user_id": user_id,
                },
            )

            return {
                "request_id": request_id,
                "status": "success",
                "data": result,
            }

        except Exception as exc:
            self.audit_logger.log_run(
                request_id=request_id,
                duration_ms=(perf_counter() - started) * 1000,
                state="error",
                verification_status="not_verified",
                lineage={"source": "SalesforceMCP"},
                error_code=type(exc).__name__,
            )
            raise

    def search_metadata(
        self,
        query: str,
        user_id: str,
    ) -> list[str]:
        """Search only objects available to the specified user."""
        if not user_id or not user_id.strip():
            raise PermissionError("A user identity is required.")

        if not query or not query.strip():
            return []

        objects = self.client.get_accessible_objects(user_id)
        search_term = query.casefold().strip()

        return [
            obj
            for obj in objects
            if search_term in obj.casefold()
        ]

    def get_data_lineage(self, request_id: str) -> dict[str, Any]:
        """Return lineage from a stored audit record, if available."""
        record = self.audit_logger.find_by_request_id(request_id)

        if record is None:
            raise LookupError(
                f"No audit or lineage record found for '{request_id}'."
            )

        return {
            "request_id": request_id,
            "lineage": record.get("lineage", {}),
            "state": record.get("state"),
            "verification_status": record.get("verification_status"),
        }

    def get_audit_trail(self, audit_id: str) -> dict[str, Any]:
        """Look up a stored audit record by request ID."""
        record = self.audit_logger.find_by_request_id(audit_id)

        if record is None:
            raise LookupError(f"Audit record '{audit_id}' was not found.")

        return record
