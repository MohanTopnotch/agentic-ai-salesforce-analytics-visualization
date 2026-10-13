
import re


class SOQLSafetyGuard:
    """Validate read-only SOQL against approved objects and fields."""

    _QUERY_PATTERN = re.compile(
        r"\s*SELECT\s+(?P<select>.*?)\s+"
        r"FROM\s+(?P<object>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s+WHERE\s+(?P<where>.*?))?"
        r"(?:\s+GROUP\s+BY\s+(?P<group>.*?))?"
        r"(?:\s+ORDER\s+BY\s+(?P<order>.*?))?"
        r"(?:\s+LIMIT\s+(?P<limit>\d+))?\s*",
        re.IGNORECASE,
    )

    _FIELD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    _AGGREGATE_PATTERN = re.compile(
        r"(COUNT|SUM|AVG|MIN|MAX)\s*\(\s*"
        r"([A-Za-z_][A-Za-z0-9_]*|\*)?\s*\)"
        r"(?:\s+AS\s+([A-Za-z_][A-Za-z0-9_]*))?",
        re.IGNORECASE,
    )
    _CONDITION_PATTERN = re.compile(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*"
        r"(NOT\s+IN|IN|LIKE|!=|<=|>=|=|<|>)\s*(.+)",
        re.IGNORECASE,
    )

    def validate_query(
        self,
        soql: str,
        user_id: str,
        accessible_objects: set[str],
        accessible_fields: dict[str, set[str]],
    ) -> str:
        """Return a query only if its grammar and access checks pass."""
        if not isinstance(soql, str) or not soql.strip():
            raise ValueError("SOQL query must not be empty.")

        if not user_id or not user_id.strip():
            raise PermissionError("A user identity is required.")

        query = soql.strip()

        # Disallow multiple statements, comments, and statement terminators.
        if any(token in query for token in (";", "--", "/*", "*/")):
            raise ValueError("Comments and multiple statements are not allowed.")

        match = self._QUERY_PATTERN.fullmatch(query)
        if match is None:
            raise ValueError("Query is outside the supported SELECT grammar.")

        parts = match.groupdict()
        object_name = parts["object"]
        self.validate_object_access(object_name, accessible_objects)

        select_items = self._split_csv(parts["select"])
        group_fields = (
            self._split_csv(parts["group"]) if parts["group"] else []
        )
        output_fields: set[str] = set()
        aggregate_aliases: set[str] = set()

        for field_name in group_fields:
            self.validate_field_access(
                object_name, field_name, accessible_fields
            )
            output_fields.add(field_name)

        for expression in select_items:
            aggregate = self._AGGREGATE_PATTERN.fullmatch(expression)

            if aggregate:
                function, field_name, alias = aggregate.groups()
                function = function.upper()
                field_name = field_name or "*"

                if field_name != "*":
                    self.validate_field_access(
                        object_name, field_name, accessible_fields
                    )

                if function != "COUNT" and field_name == "*":
                    raise ValueError(
                        f"{function}(*) is not supported by this guard."
                    )

                if alias:
                    aggregate_aliases.add(alias)
                    output_fields.add(alias)
                else:
                    output_fields.add(f"expr{len(aggregate_aliases)}")
                continue

            if not self._FIELD_PATTERN.fullmatch(expression):
                raise ValueError("Unsupported SELECT expression.")

            self.validate_field_access(
                object_name, expression, accessible_fields
            )
            output_fields.add(expression)

        if parts["where"]:
            for condition in self._split_conditions(parts["where"]):
                condition_match = self._CONDITION_PATTERN.fullmatch(
                    condition.strip()
                )
                if condition_match is None:
                    raise ValueError("Unsupported WHERE condition.")

                field_name, _operator, value = condition_match.groups()
                if not value.strip():
                    raise ValueError("WHERE condition requires a value.")

                self.validate_field_access(
                    object_name, field_name, accessible_fields
                )

        if parts["order"]:
            order_match = re.fullmatch(
                r"\s*([A-Za-z_][A-Za-z0-9_]*)"
                r"(?:\s+(ASC|DESC))?\s*",
                parts["order"],
                re.IGNORECASE,
            )
            if order_match is None:
                raise ValueError("Unsupported ORDER BY expression.")

            order_field = order_match.group(1)
            if order_field not in output_fields:
                raise ValueError(
                    "ORDER BY must reference a field in the query results."
                )

        if parts["limit"] is not None and int(parts["limit"]) < 1:
            raise ValueError("LIMIT must be greater than zero.")

        return query

    def validate_object_access(
        self,
        object_name: str,
        accessible_objects: set[str],
    ) -> None:
        """Reject objects not explicitly present in the allowlist."""
        if object_name not in accessible_objects:
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
        allowed_fields = accessible_fields.get(object_name)
        if allowed_fields is None or field_name not in allowed_fields:
            raise PermissionError(
                f"Access to field '{field_name}' on "
                f"'{object_name}' is denied."
            )

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        """Split comma-separated items while respecting quoted strings."""
        items: list[str] = []
        start = 0
        quote: str | None = None

        for index, char in enumerate(value):
            if char == "'" and quote is None:
                quote = char
            elif char == "'" and quote == "'":
                quote = None
            elif char == "," and quote is None:
                items.append(value[start:index].strip())
                start = index + 1

        if quote is not None:
            raise ValueError("Unterminated quoted value.")

        items.append(value[start:].strip())
        if any(not item for item in items):
            raise ValueError("Empty query expression is not allowed.")

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
                separator = re.match(
                    r"\s+(?:AND|OR)\s+", value[index:], re.IGNORECASE
                )
                if separator:
                    parts.append(value[start:index].strip())
                    index += separator.end()
                    start = index
                    continue

            index += 1

        if quote is not None:
            raise ValueError("Unterminated quoted WHERE value.")

        parts.append(value[start:].strip())
        if any(not part for part in parts):
            raise ValueError("Invalid WHERE condition.")
        return parts
