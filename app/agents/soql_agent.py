from typing import Any, ClassVar

from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class SOQLGenerationAgent(BaseAgent):
    """Build, validate, and execute a restricted read-only SOQL query."""

    name = "soql_generation"

    FIELD_ALIASES: ClassVar[dict[str, tuple[str, ...]]] = {
        "revenue": ("AnnualRevenue", "Amount", "Revenue__c"),
        "annual revenue": ("AnnualRevenue", "Annual_Revenue__c"),
        "sales": ("Amount", "AnnualRevenue"),
        "region": ("Region__c", "Region"),
        "lead source": ("LeadSource",),
        "industry": ("Industry",),
        "stage": ("StageName",),
        "owner": ("OwnerId",),
        "rating": ("Rating",),
        "company": ("Company",),
        "count": ("Id",),
        "record count": ("Id",),
    }

    def __init__(self, salesforce_client: Any, safety_guard: Any) -> None:
        self.salesforce_client = salesforce_client
        self.safety_guard = safety_guard

    def run(self, context: AgentContext) -> AgentResult:
        provenance = AgentProvenance(
            agent_name=self.name,
            input_request_id=context.request_id,
            source_refs=("intent", "salesforce_metadata"),
        )

        try:
            intent = context.intent
            if not isinstance(intent, dict) or not intent:
                return self._clarification(
                    context,
                    provenance,
                    "The query intent is missing. Please clarify what data "
                    "you want to analyze.",
                )

            if not context.user_id:
                raise PermissionError(
                    "A user identity is required before query execution."
                )

            accessible_objects = set(
                self.salesforce_client.get_accessible_objects(context.user_id)
            )
            if not accessible_objects:
                raise PermissionError("No Salesforce objects are accessible.")

            requested_fields = self._requested_fields(intent)
            if not requested_fields:
                return self._clarification(
                    context,
                    provenance,
                    "Please specify the metric or fields to retrieve.",
                )

            object_name, description, resolved_fields = (
                self._resolve_object_and_fields(
                    intent,
                    requested_fields,
                    accessible_objects,
                )
            )

            field_names = set(description.get("field_names", []))
            if not field_names:
                field_names = {
                    item["name"]
                    for item in description.get("fields", [])
                    if isinstance(item, dict) and item.get("name")
                }

            # The mock client currently exposes object-level access only.
            # This schema list is not a substitute for Salesforce field-level
            # security (FLS); enforce real FLS in the live connector.
            accessible_fields = {object_name: field_names}

            soql = self._build_query(
                intent=intent,
                object_name=object_name,
                resolved_fields=resolved_fields,
                accessible_fields=field_names,
            )
            validated_soql = self.safety_guard.validate_query(
                soql=soql,
                user_id=context.user_id,
                accessible_objects=accessible_objects,
                accessible_fields=accessible_fields,
            )

            response = self.salesforce_client.query(validated_soql)
            if not isinstance(response, dict):
                raise TypeError("Salesforce client returned an invalid response.")

            records = response.get("records")
            if not isinstance(records, list):
                raise TypeError(
                    "Salesforce client returned an invalid records payload."
                )

            context.soql_query = validated_soql
            context.raw_records = records
            context.query_results = records
            context.metadata.setdefault("query", {})
            context.metadata["query"].update(
                {
                    "object_name": object_name,
                    "selected_fields": resolved_fields,
                    "total_size": response.get("totalSize", len(records)),
                }
            )

            return AgentResult(
                status="success",
                output={
                    "soql_query": validated_soql,
                    "object_name": object_name,
                    "selected_fields": resolved_fields,
                    "records": records,
                    "record_count": len(records),
                },
                provenance=provenance,
                validation_status="passed",
            )

        except (PermissionError, ValueError, TypeError, KeyError) as exc:
            return AgentResult(
                status="error",
                output={},
                provenance=provenance,
                validation_status="failed",
                error=str(exc),
            )
        except Exception:  # noqa: BLE001 - fail closed at the connector boundary
            # Do not expose internal exception details, credentials, or provider
            # responses to the caller. Log the exception in the audit layer.
            return AgentResult(
                status="error",
                output={},
                provenance=provenance,
                validation_status="failed",
                error="SOQL generation or execution failed.",
            )

    @staticmethod
    def _requested_fields(intent: dict[str, Any]) -> list[str]:
        """Collect unique field names from the structured intent."""
        requested: list[str] = []

        for key in ("fields", "metrics", "group_by"):
            values = intent.get(key, [])
            if isinstance(values, str):
                values = [values]

            if isinstance(values, list):
                for value in values:
                    if (
                        isinstance(value, str)
                        and value.strip()
                        and value.strip().lower()
                        not in {item.lower() for item in requested}
                    ):
                        requested.append(value.strip())
        return requested

    def _resolve_object_and_fields(
        self,
        intent: dict[str, Any],
        requested_fields: list[str],
        accessible_objects: set[str],
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Resolve one accessible object that contains all requested fields."""
        explicit_object = (
            intent.get("object_name")
            or intent.get("object")
            or intent.get("entity")
        )

        if explicit_object:
            if not isinstance(explicit_object, str):
                raise TypeError("The requested object name must be a string.")
            candidates = [explicit_object]
        else:
            candidates = sorted(accessible_objects)

        matches: list[tuple[str, dict[str, Any], list[str]]] = []
        for object_name in candidates:
            if object_name not in accessible_objects:
                continue

            description = self.salesforce_client.describe_object(object_name)
            if not isinstance(description, dict):
                raise TypeError("Salesforce metadata response must be an object.")

            available_fields = set(description.get("field_names", []))
            if not available_fields:
                available_fields = {
                    item["name"]
                    for item in description.get("fields", [])
                    if isinstance(item, dict) and item.get("name")
                }

            resolved: list[str] = []
            for requested in requested_fields:
                field_name = self._resolve_field(requested, available_fields)
                if field_name is None:
                    break
                resolved.append(field_name)
            else:
                matches.append((object_name, description, resolved))

        if not matches:
            raise ValueError(
                "Could not resolve the requested fields to one accessible "
                "Salesforce object. Check the intent and discovered schema."
            )

        if len(matches) > 1 and not explicit_object:
            # Only choose automatically when exact matches identify one winner.
            exact_scores = [
                sum(
                    requested.lower() == resolved.lower()
                    for requested, resolved in zip(requested_fields, fields)
                )
                for _, _, fields in matches
            ]
            highest = max(exact_scores)
            winners = [
                match
                for match, score in zip(matches, exact_scores)
                if score == highest
            ]
            if len(winners) != 1:
                raise ValueError(
                    "The requested fields match multiple Salesforce objects. "
                    "Please specify the object to analyze."
                )
            return winners[0]

        return matches[0]

    def _resolve_field(
        self,
        requested: str,
        available_fields: set[str],
    ) -> str | None:
        """Resolve a semantic field name against the discovered schema."""
        if requested in available_fields:
            return requested

        case_insensitive = {field.lower(): field for field in available_fields}
        if requested.lower() in case_insensitive:
            return case_insensitive[requested.lower()]

        aliases = self.FIELD_ALIASES.get(requested.lower(), ())
        for alias in aliases:
            if alias in available_fields:
                return alias
            if alias.lower() in case_insensitive:
                return case_insensitive[alias.lower()]

        return None

    def _build_query(
        self,
        intent: dict[str, Any],
        object_name: str,
        resolved_fields: list[str],
        accessible_fields: set[str],
    ) -> str:
        """Build SOQL from structured values rather than raw query fragments."""
        if not resolved_fields:
            raise ValueError("At least one field must be selected.")

        select_clause = ", ".join(dict.fromkeys(resolved_fields))
        clauses = [f"SELECT {select_clause}", f"FROM {object_name}"]

        conditions: list[str] = []
        filters = intent.get("filters", [])
        if not isinstance(filters, list):
            raise TypeError("Filters must be provided as a list.")

        for item in filters:
            if not isinstance(item, dict):
                raise TypeError("Each filter must be a structured object.")

            requested_field = item.get("field")
            operator = str(item.get("operator", "=")).upper()
            value = item.get("value")
            if not isinstance(requested_field, str):
                raise TypeError("A filter field must be a string.")

            field_name = self._resolve_field(requested_field, accessible_fields)
            if field_name is None:
                raise ValueError(f"Unsupported filter field: {requested_field}")

            if operator not in {"=", "!=", "<", ">", "<=", ">=", "LIKE"}:
                raise ValueError(f"Unsupported filter operator: {operator}")

            conditions.append(
                f"{field_name} {operator} {self._format_value(value)}"
            )

        if conditions:
            clauses.append("WHERE " + " AND ".join(conditions))

        sort = intent.get("sort")
        if sort:
            if isinstance(sort, str):
                sort_field, direction = sort, "ASC"
            elif isinstance(sort, dict):
                sort_field = sort.get("field")
                direction = str(sort.get("direction", "ASC")).upper()
            else:
                raise TypeError("Sort must be a field name or object.")

            if not isinstance(sort_field, str) or not sort_field.strip():
                raise TypeError("Sort field must be a non-empty string.")

            resolved_sort = self._resolve_field(sort_field, accessible_fields)
            if resolved_sort is None:
                raise ValueError("Sort field is not available.")
            if direction not in {"ASC", "DESC"}:
                raise ValueError("Sort direction must be ASC or DESC.")
            if resolved_sort not in resolved_fields:
                raise ValueError("Sort field must be selected in the query.")

            clauses.append(f"ORDER BY {resolved_sort} {direction}")

        raw_limit = intent.get("limit", 100)
        if isinstance(raw_limit, bool) or not isinstance(raw_limit, int):
            raise TypeError("Query limit must be an integer.")
        if not 1 <= raw_limit <= 1000:
            raise ValueError("Query limit must be between 1 and 1000.")

        clauses.append(f"LIMIT {raw_limit}")
        return " ".join(clauses)

    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a structured literal; never accept raw SOQL fragments."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if "\x00" in value:
                raise ValueError("Filter value contains an invalid character.")
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
        raise TypeError(
            "Filter values must be strings, numbers, booleans, or null."
        )

    @staticmethod
    def _clarification(
        context: AgentContext,
        provenance: AgentProvenance,
        question: str,
    ) -> AgentResult:
        """Return a clarification request without executing a query."""
        del context  # The signature keeps call sites uniform across agent helpers.
        return AgentResult(
            status="needs_clarification",
            output={"clarification_question": question},
            provenance=provenance,
            validation_status="pending",
        )
