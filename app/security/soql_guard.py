import re

class UnsafeSOQL(ValueError):
    pass

FORBIDDEN = re.compile(r"\\b(insert|update|delete|upsert|undelete|merge|drop|alter|truncate|create)\\b", re.I)

def validate_read_only_soql(soql: str, allowed_objects: set[str] | None = None) -> str:
    """Minimal starter guard only. Replace with a SOQL-aware parser before real use."""
    query = soql.strip()
    if not query:
        raise UnsafeSOQL("SOQL query cannot be empty.")
    if ";" in query:
        raise UnsafeSOQL("Multiple statements are not allowed.")
    if FORBIDDEN.search(query):
        raise UnsafeSOQL("Mutating or DDL-like keywords are not allowed.")
    if not re.match(r"^(SELECT|WITH)\\b", query, re.I):
        raise UnsafeSOQL("Only read-oriented SELECT queries are allowed.")
    if allowed_objects is not None:
        for obj in re.findall(r"\\bFROM\\s+([A-Za-z_][A-Za-z0-9_]*__?c?)", query, re.I):
            if obj not in allowed_objects:
                raise UnsafeSOQL(f"Object is not allowlisted: {obj}")
    return query
