import re


class UnsafeSOQL(ValueError):
    """Raised when a SOQL query fails security checks."""


class SOQLSafetyGuard:
    """Validate read-only SOQL against approved objects and fields."""

    _QUERY_PATTERN = re.compile(
        r"\s*SELECT\s+(?P<select>.+?)\s+"
        r"FROM\s+(?P<object>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s+WHERE\s+(?P<where>.+?))?"
        r"(?:\s+GROUP\s+BY\s+(?P<group>.+?))?"
        r"(?:\s+ORDER\s+BY\s+(?P<order>.+?))?"
        r"(?:\s+LIMIT\s+(?P<limit>\d+))?\s*",
        re.IGNORECASE | re.DOTALL,
    )

    _FIELD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _AGGREGATE_PATTERN = re.compile(
        r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*"
        r"(DISTINCT\s+)?([A-Za-z_][A-Za-z0-9_]*|\*)?\s*\)"
        r"(?:\s+AS\s+([A-Za-z_][A-Za-z0-9_]*))?",
        re.IGNORECASE,
    )
    _CONDITION_PATTERN = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"(NOT\s+IN|IN|LIKE|!=|<=|>=|=|<|>)\s*(.+)",
        re.IGNORECASE | re.DOTALL,
    )
    _FORBIDDEN_KEYWORDS = re.compile(
        r"\b(?:DELETE|UPDATE|INSERT|UPSERT|MERGE|UNDELETE|DROP|ALTER|"
        r"TRUNCATE|EXECUTE)\b",
        re.IGNORECASE,
    )

    def validate_query(
        self,
        soql: str,
        user_id: str,
        accessible_objects: set[str],
        accessible_fields: dict[str, set[str]] | None,
    ) -> str:
        """Return a query only if its grammar and access checks pass."""
        if not isinstance(soql, str) or not soql.strip():
            raise UnsafeSOQL("SOQL query must not be empty.")

        if not isinstance(user_id, str) or not user_id.strip():
            raise PermissionError("A user identity is required.")

        if not accessible_objects:
            raise PermissionError("No Salesforce objects are permitted.")

        if accessible_fields is None:
            raise PermissionError("Field permissions are required.")

        query = soql.strip()

        # Disallow multiple statements, comments, and statement terminators.
        if any(token in query for token in (";", "--", "/*", "*/")):
            raise UnsafeSOQL("Comments and multiple statements are not allowed.")

        if any(ord(char) < 32 and char not in "\t\n\r" for char in query):
            raise UnsafeSOQL("Control characters are not allowed.")

        if self._FORBIDDEN_KEYWORDS.search(query):
            raise UnsafeSOQL("Mutation or administrative keywords are forbidden.")

        match = self._QUERY_PATTERN.fullmatch(query)
        if match is None:
            raise UnsafeSOQL("Query is outside the supported SELECT grammar.")

        parts = match.groupdict()
        object_name = parts["object"]
        self.validate_object_access(object_name, accessible_objects)

        select_items = self._split_csv(parts["select"])
        group_fields = self._split_csv(parts["group"]) if parts["group"] else []
        output_fields: set[str] = set()
        aggregate_aliases: set[str] = set()

        for field_name in group_fields:
            if not self._FIELD_PATTERN.fullmatch(field_name):
                raise UnsafeSOQL("Unsupported GROUP BY expression.")
            self.validate_field_access(object_name, field_name, accessible_fields)
            output_fields.add(field_name.casefold())

        for expression in select_items:
            aggregate = self._AGGREGATE_PATTERN.fullmatch(expression)

            if aggregate:
                function, distinct, field_name, alias = aggregate.groups()
                function = function.upper()
                field_name = field_name or ""

                if distinct and (
                    function != "COUNT" or not field_name or field_name == "*"
                ):
                    raise UnsafeSOQL("DISTINCT is supported only for COUNT(field).")

                if field_name == "*" and function != "COUNT":
                    raise UnsafeSOQL(f"{function}(*) is not supported by this guard.")

                if field_name:
                    if field_name == "*":
                        if function != "COUNT":
                            raise UnsafeSOQL("Only COUNT(*) may use '*'.")
                    else:
                        self.validate_field_access(
                            object_name, field_name, accessible_fields
                        )

                if alias:
                    alias_key = alias.casefold()
                    if alias_key in aggregate_aliases:
                        raise UnsafeSOQL("Aggregate aliases must be unique.")
                    aggregate_aliases.add(alias_key)
                    output_fields.add(alias_key)
                else:
                    output_fields.add(f"expr{len(aggregate_aliases)}".casefold())
                continue

            if not self._FIELD_PATTERN.fullmatch(expression):
                raise UnsafeSOQL("Unsupported SELECT expression.")

            self.validate_field_access(object_name, expression, accessible_fields)
            output_fields.add(expression.casefold())

        # GROUP BY queries must select each grouped field.
        if group_fields and not {field.casefold() for field in group_fields}.issubset(
            output_fields
        ):
            raise UnsafeSOQL("GROUP BY fields must appear in SELECT.")

        if parts["where"]:
            for condition in self._split_conditions(parts["where"]):
                condition_match = self._CONDITION_PATTERN.fullmatch(condition.strip())
                if condition_match is None:
                    raise UnsafeSOQL("Unsupported WHERE condition.")

                field_name, operator, value = condition_match.groups()
                if not value.strip():
                    raise UnsafeSOQL("WHERE condition requires a value.")

                self.validate_field_access(object_name, field_name, accessible_fields)
                self._validate_condition_value(operator, value)

        if parts["order"]:
            order_items = self._split_csv(parts["order"])
            for order_item in order_items:
                order_match = re.fullmatch(
                    r"\s*([A-Za-z_][A-Za-z0-9_]*)"
                    r"(?:\s+(ASC|DESC))?\s*",
                    order_item,
                    re.IGNORECASE,
                )
                if order_match is None:
                    raise UnsafeSOQL("Unsupported ORDER BY expression.")

                order_field = order_match.group(1).casefold()
                # Preserve the existing rule: ORDER BY must reference a
                # selected field or aggregate alias.
                if order_field not in output_fields:
                    raise UnsafeSOQL(
                        "ORDER BY must reference a field in the query results."
                    )

        if parts["limit"] is not None and int(parts["limit"]) < 1:
            raise UnsafeSOQL("LIMIT must be greater than zero.")

        return query

    def validate_object_access(
        self,
        object_name: str,
        accessible_objects: set[str],
    ) -> None:
        """Reject objects not explicitly present in the allowlist."""
        allowed_objects = {name.casefold() for name in accessible_objects}
        if object_name.casefold() not in allowed_objects:
            raise PermissionError(
                f"Access to Salesforce object '{object_name}' is denied."
            )

    def validate_field_access(
        self,
        object_name: str,
        field_name: str,
        accessible_fields: dict[str, set[str]],
    ) -> None:
        """Reject fields missing from the object's field allowlist."""
        allowed_fields = next(
            (
                fields
                for name, fields in accessible_fields.items()
                if name.casefold() == object_name.casefold()
            ),
            None,
        )
        if allowed_fields is None or field_name.casefold() not in {
            field.casefold() for field in allowed_fields
        }:
            raise PermissionError(
                f"Access to field '{field_name}' on '{object_name}' is denied."
            )

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        """Split comma-separated items while respecting quoted strings."""
        items: list[str] = []
        start = 0
        quote: str | None = None
        index = 0

        while index < len(value):
            char = value[index]

            if char == "'" and quote is None:
                quote = char
            elif char == "'" and quote == "'":
                # SOQL escapes a quote by doubling it.
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 1
                else:
                    quote = None
            elif char == "," and quote is None:
                items.append(value[start:index].strip())
                start = index + 1

            index += 1

        if quote is not None:
            raise UnsafeSOQL("Unterminated quoted value.")

        items.append(value[start:].strip())
        if any(not item for item in items):
            raise UnsafeSOQL("Empty query expression is not allowed.")

        return items

    @staticmethod
    def _split_conditions(value: str) -> list[str]:
        """Split AND/OR conditions without splitting quoted text."""
        parts: list[str] = []
        start = 0
        quote: str | None = None
        index = 0

        while index < len(value):
            char = value[index]

            if char == "'" and quote is None:
                quote = char
            elif char == "'" and quote == "'":
                # SOQL escapes a quote by doubling it.
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 1
                else:
                    quote = None
            elif quote is None:
                separator = re.match(r"\s+(AND|OR)\s+", value[index:], re.IGNORECASE)
                if separator:
                    parts.append(value[start:index].strip())
                    index += separator.end()
                    start = index
                    continue

            index += 1

        if quote is not None:
            raise UnsafeSOQL("Unterminated quoted WHERE value.")

        parts.append(value[start:].strip())
        if any(not part for part in parts):
            raise UnsafeSOQL("Invalid WHERE condition.")
        return parts

    @staticmethod
    def _validate_condition_value(operator: str, value: str) -> None:
        """Reject nested queries and malformed condition values."""
        value = value.strip()
        normalized_operator = operator.upper()

        if normalized_operator in {"IN", "NOT IN"}:
            if not (value.startswith("(") and value.endswith(")")):
                raise UnsafeSOQL("IN and NOT IN require a parenthesized literal list.")

            inner = value[1:-1].strip()

            if not inner:
                raise UnsafeSOQL("IN lists cannot be empty.")

            if re.search(r"\bSELECT\b", inner, re.IGNORECASE):
                raise UnsafeSOQL("Nested queries are not supported.")

            values = SOQLSafetyGuard._split_csv(inner)

            for item in values:
                if not SOQLSafetyGuard._is_literal(item):
                    raise UnsafeSOQL("Unsupported IN-list value.")

            return

        if value.startswith("(") or value.endswith(")"):
            raise UnsafeSOQL("Parenthesized values require IN or NOT IN.")

        if re.search(r"\bSELECT\b", value, re.IGNORECASE):
            raise UnsafeSOQL("Nested queries are not supported.")

        if not SOQLSafetyGuard._is_literal(value):
            raise UnsafeSOQL("Unsupported WHERE value.")

        """Reject nested query syntax and malformed condition values."""
        value = value.strip()

        # Values are intentionally restricted to literals or literal lists.
        if value.startswith("(") and value.endswith(")"):
            if re.search(r"(?i)\bSELECT\b", value):
                raise UnsafeSOQL("Nested queries are not supported.")
            if operator.upper() not in {"IN", "NOT IN"}:
                raise UnsafeSOQL("Parenthesized values require IN or NOT IN.")
            inner = value[1:-1].strip()
            if not inner:
                raise UnsafeSOQL("IN lists cannot be empty.")
            values = SOQLSafetyGuard._split_csv(inner)
            for item in values:
                if not SOQLSafetyGuard._is_literal(item):
                    raise UnsafeSOQL("Unsupported IN-list value.")
            return

        if operator.upper() in {"IN", "NOT IN"}:
            raise UnsafeSOQL("IN and NOT IN require a parenthesized literal list.")

        if not SOQLSafetyGuard._is_literal(value):
            raise UnsafeSOQL("Unsupported WHERE value.")

    @staticmethod
    def _is_literal(value: str) -> bool:
        value = value.strip()
        return bool(
            re.fullmatch(r"'(?:[^']|'')*'", value)
            or re.fullmatch(r"-?\d+(?:\.\d+)?", value)
            or re.fullmatch(r"(?i:NULL|TRUE|FALSE)", value)
        )
