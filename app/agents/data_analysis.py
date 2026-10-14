from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.analysis.calculation import safe_sum
from app.analysis.verification import verify_reconciliation


class DataAnalysisAgent(BaseAgent):
    name = "data_analysis"

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Convert a valid numeric value without losing decimal precision."""
        if value is None or isinstance(value, bool):
            raise ValueError("Metric values must be valid numbers.")

        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("Metric values must be valid numbers.") from exc

        if not number.is_finite():
            raise ValueError("Metric values must be finite numbers.")

        return number

    def run(self, context: AgentContext) -> AgentResult:
        records = context.raw_records

        if not records:
            context.calculated_data = []
            context.verification = {
                "status": "unverified",
                "checks_passed": 0,
                "checks_failed": 1,
                "reconciliation_delta": None,
                "reason": "No records available for analysis.",
            }
            return AgentResult(
                status="error",
                output={
                    "calculated_data": [],
                    "verification": context.verification,
                },
                validation_status="failed",
                error="No records available for analysis.",
            )

        config = context.metadata.get("analysis", {})
        metric = config.get("metric", "Amount")
        dimension = config.get("dimension", "Region")

        try:
            values_by_group: dict[str, list[Decimal]] = defaultdict(list)
            validated_values: list[Decimal] = []

            # Validate every metric before aggregating anything.
            for row in records:
                if metric not in row:
                    raise ValueError(
                        f"Required metric field '{metric}' is missing."
                    )

                value = self._to_decimal(row[metric])
                group_value = row.get(dimension)
                group_name = (
                    str(group_value)
                    if group_value is not None
                    else "Unknown"
                )

                validated_values.append(value)
                values_by_group[group_name].append(value)

            # Reuse the existing deterministic Decimal calculation.
            grand_total = safe_sum(validated_values)

            calculated_data = [
                {
                    dimension: group,
                    metric: safe_sum(group_values),
                }
                for group, group_values in sorted(values_by_group.items())
            ]

            # Independently reconcile group totals against the raw total.
            reconciliation = verify_reconciliation(
                [
                    self._to_decimal(row[metric])
                    for row in calculated_data
                ],
                grand_total,
            )

            # Preserve the reconciliation contract while using
            # "unverified" for an unsuccessful analytical result.
            verification = {
                **reconciliation,
                "status": (
                    "verified"
                    if reconciliation["status"] == "verified"
                    else "unverified"
                ),
                "reason": (
                    "Raw-record and grouped totals reconciled."
                    if reconciliation["status"] == "verified"
                    else "Grouped totals do not reconcile with the raw-record total."
                ),
            }

            context.calculated_data = calculated_data
            context.verification = verification

            passed = verification["status"] == "verified"

            return AgentResult(
                status="success" if passed else "error",
                output={
                    "calculated_data": calculated_data,
                    "verification": verification,
                },
                validation_status="passed" if passed else "failed",
                error=None if passed else verification["reason"],
            )

        except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
            context.calculated_data = []
            context.verification = {
                "status": "unverified",
                "checks_passed": 0,
                "checks_failed": 1,
                "reconciliation_delta": None,
                "reason": f"Analysis input validation failed: {exc}",
            }

            return AgentResult(
                status="error",
                output={
                    "calculated_data": [],
                    "verification": context.verification,
                },
                validation_status="failed",
                error="Could not calculate or verify the requested metrics.",
            )
