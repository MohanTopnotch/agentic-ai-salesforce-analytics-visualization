# Explain observed results, identify outliers, and provide evidence-backed insights. Clearly label possible causes as hypotheses when they have not been established by the data.from app.agents.base
from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class InsightAgent(BaseAgent):
    name = "insight"

    def run(self, context: AgentContext) -> AgentResult:
        verification = context.verification
        rows = context.calculated_data

        if verification.get("status") != "verified":
            return AgentResult(
                status="error",
                output={
                    "insights": [],
                    "diagnostic": (
                        "Insights were not generated because "
                        "the analytical results are not verified."
                    ),
                },
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("verification",),
                ),
                validation_status="failed",
                # error ="Analysis verification is required.",
            )

        if not rows:
            return AgentResult(
                status="success",
                output={
                    "insights": [],
                    "diagnostic": "No data is available to summarize.",
                },
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("calculated_data", "verification"),
                ),
                validation_status="passed",
            )

        insights = []

        for row in rows:
            region = row.get("Region")
            amount = row.get("Amount")
            count = row.get("OpportunityCount")

            if region is None or amount is None:
                continue

            try:
                numeric_amount = float(amount)
            except (TypeError, ValueError, OverflowError):
                continue

            message = f"Sales for {region} totaled ${numeric_amount:,.2f}."

            if count is not None:
                message = (
                    f"Closed-won sales for {region} totaled "
                    f"${numeric_amount:,.2f} across "
                    f"{count} opportunities."
                )

            insights.append(message)
            region = row.get("Region")
            amount = row.get("Amount")
            count = row.get("OpportunityCount")

            # Only use a template when its required fields exist.
            if region is not None and amount is not None:
                message = f"Sales for {region} totaled ${float(amount):,.2f}."

                if count is not None:
                    message = (
                        f"Closed-won sales for {region} totaled "
                        f"${float(amount):,.2f} across "
                        f"{count} opportunities."
                    )

                insights.append(message)

        context.insights = insights

        return AgentResult(
            status="success",
            output={"insights": insights},
            provenance=AgentProvenance(
                agent_name=self.name,
                input_request_id=context.request_id,
                source_refs=("calculated_data", "verification"),
            ),
            validation_status="passed",
        )
