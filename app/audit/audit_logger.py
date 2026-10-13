import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, log_path: str = "logs/audit.jsonl"):
        self.log_path = Path(log_path)
        self._lock = threading.Lock()

    @staticmethod
    def _redact_query(query: str | None) -> str | None:
        if not query:
            return query

        # Redact quoted SOQL literals before writing the audit record.
        return re.sub(
            r"'(?:''|\\.|[^'])*'",
            "'[REDACTED]'",
            query,
        )

    def log_run(
        self,
        *,
        request_id: str,
        duration_ms: float,
        state: str,
        soql_query: str | None,
        verification_status: str,
        lineage: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
            "duration_ms": round(duration_ms, 2),
            "state": state,
            "soql_query": self._redact_query(soql_query),
            "verification_status": verification_status,
            "lineage": lineage or {},
            "error_code": error_code,
        }

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock, self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, default=str) + "\n")