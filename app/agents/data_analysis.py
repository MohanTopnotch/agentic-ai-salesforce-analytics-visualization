
from collections import defaultdict

from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class DataAnalysisAgent(BaseAgent):
    name = "data_analysis"

    def run(self, context: AgentContext) -> AgentResult:
        records = context.raw_records

        if not records:
            context.calculated_data = []
            context.verification = {
                "status": "unverified",
                "checks_passed": 0,
                "checks_failed": 0,
                "reconciliation_delta": None,
                "reason": "No records available for analysis.",
            }

            return AgentResult(
                status="success",
                output={
                    "calculated_data": [],
                    "verification": context.verification,
                },
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("raw_records",),
                ),
                validation_status="failed",
                error_message="Could not calculate or verify the requested metrics.",
            )

        try:
            # Optional analysis configuration:
            # context.metadata["analysis"] = {
            #     "metric": "Amount",
            #     "dimension": "Region",
            # }
            config = context.metadata.get("analysis", {})
            metric = config.get("metric", "Amount")
            dimension = config.get("dimension", "Region")

            # Calculate the total directly from the raw records.
            total_from_records = sum(
                float(row[metric])
                for row in records
                if row.get(metric) is not None
            )

            # Independently calculate totals for each group.
            grouped_totals: dict[str, float] = defaultdict(float)

            for row in records:
                value = row.get(metric)
                group = row.get(dimension)

                if value is None:
                    continue

                group_name = (
                    str(group) if group is not None else "Unknown"
                )
                grouped_totals[group_name] += float(value)

            calculated_data = [
                {
                    dimension: group,
                    metric: total,
                }
                for group, total in grouped_totals.items()
            ]

            # Reconcile the grouped total with the raw-record total.
            total_from_groups = sum(grouped_totals.values())
            delta = abs(total_from_records - total_from_groups)
            passed = delta < 0.01

            context.calculated_data = calculated_data
            context.verification = {
                "status": "verified" if passed else "unverified",
                "checks_passed": 2 if passed else 1,
                "checks_failed": 0 if passed else 1,
                "reconciliation_delta": round(delta, 10),
            }

            return AgentResult(
                status="success",
                output={
                    "calculated_data": calculated_data,
                    "verification": context.verification,
                },
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("raw_records",),
                ),
                validation_status="passed" if passed else "failed",
            )

        except (TypeError, ValueError, KeyError):
            context.verification = {
                "status": "unverified",
                "checks_passed": 0,
                "checks_failed": 1,
                "reconciliation_delta": None,
                "reason": "Analysis input validation failed.",
            }

            return AgentResult(
                status="error",
                output={
                    "verification": context.verification,
                },
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("raw_records",),
                ),
                validation_status="failed",
                error_message=(
                    "Could not calculate or verify the requested metrics."
                ),
            )
