from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy
from typing import Any, ClassVar

from app.salesforce.client import SalesforceClient


class SalesforceQueryError(ValueError):
    """A predictable, structured error from the mock Salesforce API."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


def _field(
    name: str,
    field_type: str,
    *,
    filterable: bool = True,
    groupable: bool = True,
    aggregatable: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": field_type,
        "filterable": filterable,
        "groupable": groupable,
        "aggregatable": aggregatable,
    }


class MockSalesforceClient(SalesforceClient):
    """In-memory Salesforce mock with a restricted SOQL interface."""

    OBJECTS: ClassVar[dict[str, Any]] = {
        "Lead": {
            "fields": {
                "Id": _field("Id", "id"),
                "FirstName": _field("FirstName", "string"),
                "LastName": _field("LastName", "string"),
                "Company": _field("Company", "string"),
                "Email": _field("Email", "email"),
                "Status": _field("Status", "string"),
                "Rating": _field("Rating", "string"),
                "Industry": _field("Industry", "string"),
                "NumberOfEmployees": _field(
                    "NumberOfEmployees", "integer", aggregatable=True
                ),
                "AnnualRevenue": _field("AnnualRevenue", "currency", aggregatable=True),
                "LeadSource": _field("LeadSource", "string"),
                "OwnerId": _field("OwnerId", "id"),
                "CreatedDate": _field("CreatedDate", "datetime"),
                "EmailBouncedDate": _field("EmailBouncedDate", "datetime"),
            }
        },
        "Opportunity": {
            "fields": {
                "Id": _field("Id", "id"),
                "Name": _field("Name", "string"),
                "Amount": _field("Amount", "currency", aggregatable=True),
                "StageName": _field("StageName", "string"),
                "CloseDate": _field("CloseDate", "date"),
                "Region": _field("Region", "string"),
            }
        }
    }

    def __init__(self, records: dict[str, list[dict]] | None = None):
        sample_records = {
            "Lead": [
                {
                    "Id": "00Q0001",
                    "FirstName": "Ava",
                    "LastName": "Sharma",
                    "Company": "TechNova",
                    "Email": "ava@technova.example",
                    "Status": "Open - Not Contacted",
                    "Rating": "Hot",
                    "Industry": "Technology",
                    "NumberOfEmployees": 250,
                    "AnnualRevenue": 8_000_000,
                    "LeadSource": "Web",
                    "OwnerId": "0050001",
                    "CreatedDate": "2026-08-01T10:00:00",
                    "EmailBouncedDate": None,
                },
                {
                    "Id": "00Q0002",
                    "FirstName": "Noah",
                    "LastName": "Patel",
                    "Company": "FinEdge",
                    "Email": "noah@finedge.example",
                    "Status": "Working",
                    "Rating": "Warm",
                    "Industry": "Finance",
                    "NumberOfEmployees": 150,
                    "AnnualRevenue": 6_000_000,
                    "LeadSource": "Referral",
                    "OwnerId": "0050001",
                    "CreatedDate": "2026-07-15T09:30:00",
                    "EmailBouncedDate": None,
                },
                {
                    "Id": "00Q0003",
                    "FirstName": "Mia",
                    "LastName": "Rao",
                    "Company": "GreenField",
                    "Email": "mia@greenfield.example",
                    "Status": "Open - Not Contacted",
                    "Rating": "Cold",
                    "Industry": "Agriculture",
                    "NumberOfEmployees": 80,
                    "AnnualRevenue": 1_000_000,
                    "LeadSource": "Web",
                    "OwnerId": "0050002",
                    "CreatedDate": "2026-06-20T11:00:00",
                    "EmailBouncedDate": None,
                },
                {
                    "Id": "00Q0004",
                    "FirstName": "Liam",
                    "LastName": "Singh",
                    "Company": "CloudWorks",
                    "Email": "liam@cloudworks.example",
                    "Status": "Open - Not Contacted",
                    "Rating": "Warm",
                    "Industry": "Technology",
                    "NumberOfEmployees": 120,
                    "AnnualRevenue": 4_000_000,
                    "LeadSource": "Web",
                    "OwnerId": "0050002",
                    "CreatedDate": "2026-08-18T12:00:00",
                    "EmailBouncedDate": None,
                },
                {
                    "Id": "00Q0005",
                    "FirstName": "Zoe",
                    "LastName": "Mehta",
                    "Company": "CapitalBridge",
                    "Email": "zoe@capitalbridge.example",
                    "Status": "Qualified",
                    "Rating": "Hot",
                    "Industry": "Finance",
                    "NumberOfEmployees": 500,
                    "AnnualRevenue": 12_000_000,
                    "LeadSource": "Partner",
                    "OwnerId": "0050001",
                    "CreatedDate": "2026-08-10T08:00:00",
                    "EmailBouncedDate": None,
                },
            ]
        }

        sample_records["Opportunity"] = [
            {
                "Id": "OPP001",
                "Name": "North Region Renewal",
                "Amount": 150_000,
                "StageName": "Closed Won",
                "CloseDate": "2026-02-15",
                "Region": "North",
            },
            {
                "Id": "OPP002",
                "Name": "West Region Expansion",
                "Amount": 250_000,
                "StageName": "Negotiation",
                "CloseDate": "2026-03-20",
                "Region": "West",
            },
            {
                "Id": "OPP003",
                "Name": "South Region Upgrade",
                "Amount": 100_000,
                "StageName": "Closed Won",
                "CloseDate": "2026-03-25",
                "Region": "South",
            },
        ]
        self._records = deepcopy(sample_records if records is None else records)

    def describe_object(self, object_name: str) -> dict[str, Any]:
        """Return metadata for a supported object."""
        obj = self.OBJECTS.get(object_name)
        if obj is None:
            raise SalesforceQueryError(
                "UNKNOWN_OBJECT",
                f"Unsupported Salesforce object: {object_name}",
                {"object": object_name},
            )

        return {
            "name": object_name,
            "fields": deepcopy(list(obj["fields"].values())),
            "field_names": list(obj["fields"]),
        }

    def get_accessible_objects(self, user_id: str | None = None) -> list[str]:
        """Return the objects available to this mock client."""
        # This mock has no user-specific permission model yet.
        return sorted(self.OBJECTS)

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        """Split comma-separated expressions outside quoted strings."""
        parts = []
        start = 0
        quote = None
        i = 0

        while i < len(value):
            char = value[i]

            if quote:
                if char == quote:
                    if i + 1 < len(value) and value[i + 1] == quote:
                        i += 1
                    else:
                        quote = None
            elif char in ("'", '"'):
                quote = char
            elif char == ",":
                parts.append(value[start:i].strip())
                start = i + 1

            i += 1

        if quote:
            raise SalesforceQueryError("INVALID_QUERY", "Unterminated string literal")

        parts.append(value[start:].strip())
        return parts

    @staticmethod
    def _literal(raw: str) -> Any:
        raw = raw.strip()

        if raw.startswith("'") and raw.endswith("'"):
            return raw[1:-1].replace("''", "'")

        if raw.startswith('"') and raw.endswith('"'):
            return raw[1:-1].replace('""', '"')

        if raw.upper() == "NULL":
            return None
        if raw.upper() == "TRUE":
            return True
        if raw.upper() == "FALSE":
            return False

        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if re.fullmatch(r"-?\d+\.\d+", raw):
            return float(raw)

        raise SalesforceQueryError(
            "INVALID_LITERAL",
            f"Unsupported literal: {raw}",
            {"literal": raw},
        )

    @staticmethod
    def _condition_parts(where: str) -> list[str]:
        """Split conditions on AND outside strings and parentheses."""
        parts = []
        start = 0
        quote = None
        depth = 0
        i = 0

        while i < len(where):
            char = where[i]

            if quote:
                if char == quote:
                    if i + 1 < len(where) and where[i + 1] == quote:
                        i += 1
                    else:
                        quote = None
            elif char in ("'", '"'):
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    raise SalesforceQueryError(
                        "INVALID_QUERY", "Unexpected closing parenthesis"
                    )
            elif (
                depth == 0
                and where[i : i + 3].upper() == "AND"
                and (i == 0 or where[i - 1].isspace())
                and (i + 3 == len(where) or where[i + 3].isspace())
            ):
                parts.append(where[start:i].strip())
                start = i + 3
                i += 2

            i += 1

        if quote or depth != 0:
            raise SalesforceQueryError(
                "INVALID_QUERY", "Unbalanced quotes or parentheses"
            )

        parts.append(where[start:].strip())
        return parts

    def _parse_condition(self, condition: str) -> tuple:
        match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s+"
            r"(NOT\s+IN|IN|LIKE|!=|>=|<=|=|>|<)\s*(.*?)",
            condition,
            re.IGNORECASE,
        )

        if not match:
            raise SalesforceQueryError(
                "UNSUPPORTED_FILTER",
                "Unsupported WHERE condition",
                {"condition": condition},
            )

        field, operator, raw = match.groups()
        operator = re.sub(r"\s+", " ", operator.upper())

        if operator in ("IN", "NOT IN"):
            if not (raw.startswith("(") and raw.endswith(")")):
                raise SalesforceQueryError(
                    "INVALID_FILTER", "IN requires a parenthesized list"
                )
            values = [self._literal(item) for item in self._split_csv(raw[1:-1])]
            if not values:
                raise SalesforceQueryError("INVALID_FILTER", "IN list cannot be empty")
            return field, operator, values

        return field, operator, self._literal(raw)

    @staticmethod
    def _matches(record: dict, condition: tuple) -> bool:
        field, operator, expected = condition
        actual = record.get(field)

        if operator == "=":
            return actual == expected
        if operator == "!=":
            return actual != expected
        if operator == "IN":
            return actual in expected
        if operator == "NOT IN":
            return actual not in expected
        if operator == "LIKE":
            if not isinstance(actual, str) or not isinstance(expected, str):
                return False
            pattern = re.escape(expected).replace(r"\%", ".*").replace(r"\_", ".")
            return re.fullmatch(pattern, actual, re.IGNORECASE) is not None

        # Never compare null values or unrelated Python types.
        if actual is None or expected is None:
            return False

        if type(actual) not in (int, float, str) or type(expected) not in (
            int,
            float,
            str,
        ):
            return False

        try:
            if operator == ">":
                return actual > expected
            if operator == "<":
                return actual < expected
            if operator == ">=":
                return actual >= expected
            if operator == "<=":
                return actual <= expected
        except TypeError:
            return False

        return False

    def query(self, soql: str) -> dict[str, Any]:
        """Execute only the supported SELECT subset against mock records."""
        if not isinstance(soql, str) or not soql.strip():
            raise SalesforceQueryError(
                "INVALID_QUERY", "Query must be a non-empty string"
            )

        # Deliberately limited grammar: no subqueries, joins, or expressions.
        match = re.fullmatch(
            r"\s*SELECT\s+(.*?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)"
            r"(?:\s+WHERE\s+(.*?))?"
            r"(?:\s+GROUP\s+BY\s+(.*?))?"
            r"(?:\s+ORDER\s+BY\s+(.*?))?"
            r"(?:\s+LIMIT\s+(\d+))?\s*",
            soql,
            re.IGNORECASE,
        )

        if not match:
            raise SalesforceQueryError(
                "UNSUPPORTED_QUERY",
                "Query is outside the supported SELECT grammar",
                {
                    "supported": [
                        "SELECT",
                        "FROM",
                        "WHERE",
                        "GROUP BY",
                        "ORDER BY",
                        "LIMIT",
                    ]
                },
            )

        select_raw, object_name, where_raw, group_raw, order_raw, limit_raw = (
            match.groups()
        )

        metadata = self.OBJECTS.get(object_name)
        if metadata is None:
            raise SalesforceQueryError(
                "UNKNOWN_OBJECT",
                f"Unsupported Salesforce object: {object_name}",
                {"object": object_name},
            )

        fields = metadata["fields"]
        selected = self._split_csv(select_raw)
        group_fields = self._split_csv(group_raw) if group_raw else []

        def validate_field(name: str, *, purpose: str = "select") -> None:
            if name not in fields:
                raise SalesforceQueryError(
                    "UNKNOWN_FIELD",
                    f"Unsupported field: {name}",
                    {"object": object_name, "field": name},
                )
            if purpose == "filter" and not fields[name]["filterable"]:
                raise SalesforceQueryError(
                    "UNSUPPORTED_FILTER", f"Field is not filterable: {name}"
                )
            if purpose == "group" and not fields[name]["groupable"]:
                raise SalesforceQueryError(
                    "UNSUPPORTED_GROUPING", f"Field is not groupable: {name}"
                )

        for name in group_fields:
            validate_field(name, purpose="group")

        aggregates = []
        plain_fields = []

        for expression in selected:
            aggregate = re.fullmatch(
                r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*"
                r"([A-Za-z_][A-Za-z0-9_]*|\*)?\s*\)"
                r"(?:\s+AS\s+([A-Za-z_][A-Za-z0-9_]*))?",
                expression,
                re.IGNORECASE,
            )

            if aggregate:
                function, field, alias = aggregate.groups()
                function = function.upper()
                field = field or "*"

                if function == "COUNT" and field == "*":
                    pass
                else:
                    validate_field(field)
                    if function in ("SUM", "AVG") and not fields[field]["aggregatable"]:
                        raise SalesforceQueryError(
                            "UNSUPPORTED_AGGREGATION",
                            f"{function} is not supported for {field}",
                        )

                aggregates.append(
                    {
                        "function": function,
                        "field": field,
                        "alias": alias or (f"expr{len(aggregates)}"),
                    }
                )
            else:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
                    raise SalesforceQueryError(
                        "UNSUPPORTED_EXPRESSION",
                        f"Unsupported SELECT expression: {expression}",
                    )
                validate_field(expression)
                plain_fields.append(expression)

        if group_fields and not aggregates:
            raise SalesforceQueryError(
                "UNSUPPORTED_GROUPING",
                "GROUP BY requires at least one aggregate function",
            )
        if (
            aggregates
            and plain_fields
            and any(field not in group_fields for field in plain_fields)
        ):
            raise SalesforceQueryError(
                "INVALID_AGGREGATION",
                "Selected non-aggregate fields must appear in GROUP BY",
            )
        conditions = []
        if where_raw:
            for raw_condition in self._condition_parts(where_raw):
                condition = self._parse_condition(raw_condition)
                validate_field(condition[0], purpose="filter")
                conditions.append(condition)
        rows = [
            deepcopy(row)
            for row in self._records.get(object_name, [])
            if all(self._matches(row, c) for c in conditions)
        ]

        if group_fields or aggregates:
            groups = defaultdict(list)

            if group_fields:
                for row in rows:
                    groups[tuple(row.get(f) for f in group_fields)].append(row)
            else:
                groups[()] = rows

            result = []
            for key, members in groups.items():
                output = dict(zip(group_fields, key))

                for aggregate in aggregates:
                    fn = aggregate["function"]
                    field = aggregate["field"]
                    values = [
                        row.get(field)
                        for row in members
                        if field == "*" or row.get(field) is not None
                    ]

                    if fn == "COUNT":
                        value = len(values)
                    elif not values:
                        value = None
                    elif fn == "SUM":
                        value = sum(values)
                    elif fn == "AVG":
                        value = sum(values) / len(values)
                    elif fn == "MIN":
                        value = min(values)
                    else:
                        value = max(values)

                    output[aggregate["alias"]] = value

                result.append(output)
        else:
            result = [{field: row.get(field) for field in selected} for row in rows]

        if order_raw:
            order_match = re.fullmatch(
                r"([A-Za-z_][A-Za-z0-9_]*)(?:\s+(ASC|DESC))?",
                order_raw.strip(),
                re.IGNORECASE,
            )
            if not order_match:
                raise SalesforceQueryError(
                    "UNSUPPORTED_ORDER",
                    "Only one ORDER BY field is supported",
                )

            order_field, direction = order_match.groups()
            direction = (direction or "ASC").upper()

            if order_field not in (
                set(plain_fields) | set(group_fields) | {a["alias"] for a in aggregates}
            ):
                raise SalesforceQueryError(
                    "INVALID_ORDER_FIELD",
                    f"ORDER BY field must appear in the result: {order_field}",
                )

            # Nulls sort after non-null values in ascending order.
            result.sort(
                key=lambda row: (
                    row.get(order_field) is None,
                    row.get(order_field) if row.get(order_field) is not None else 0,
                ),
                reverse=(direction == "DESC"),
            )

        if limit_raw:
            result = result[: int(limit_raw)]

        return {"totalSize": len(result), "records": result}
