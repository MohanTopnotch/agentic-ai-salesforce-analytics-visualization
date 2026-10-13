
import re
from typing import Any, ClassVar

from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class QueryUnderstandingAgent(BaseAgent):
    name = "query_understanding"

    INTENT_KEYWORDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "sales_by_region": (
            "sales by region",
            "revenue by region",
            "regional sales",
            "sales across regions",
        ),
        "sales_analysis": (
            "sales",
            "revenue",
            "closed won",
            "opportunities",
            "pipeline",
            "deal value",
        ),
        "lead_analysis": (
            "lead",
            "leads",
            "prospect",
            "prospects",
            "unconverted",
            "conversion rate",
        ),
        "account_analysis": (
            "account",
            "accounts",
            "customer",
            "customers",
            "industry",
        ),
        "quota_analysis": (
            "quota",
            "target",
            "sales target",
            "attainment",
        ),
        "owner_performance": (
            "sales rep",
            "sales representative",
            "owner performance",
            "salesperson",
            "sales people",
            "salesperson performance",
        ),
    }

    GROUPING_KEYWORDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "region": ("region", "regional"),
        "owner": ("owner", "sales rep", "salesperson"),
        "stage": ("stage", "sales stage"),
        "industry": ("industry", "industries"),
        "lead_source": ("lead source", "lead sources", "source"),
        "month": ("month", "monthly"),
        "quarter": ("quarter", "quarterly"),
        "year": ("year", "yearly", "annually"),
    }

    METRIC_KEYWORDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "count": ("count", "number of", "how many", "total number"),
        "revenue": ("revenue", "sales amount", "deal value"),
        "amount": ("amount", "value", "opportunity value"),
        "average": ("average", "avg", "mean"),
        "conversion_rate": ("conversion rate", "conversion percentage"),
        "quota": ("quota", "target", "attainment"),
    }

    def run(self, context: AgentContext) -> AgentResult:
        """
        Interpret a natural-language Salesforce analytics request.

        This agent identifies a likely intent and extracts basic query
        requirements. It does not generate or execute SOQL.
        """
        question = self._get_question(context)

        if not question:
            return self._result(
                context=context,
                status="needs_clarification",
                output={
                    "intent": {
                        "intent": "unknown",
                        "original_question": "",
                        "entities": [],
                        "metrics": [],
                        "group_by": [],
                        "filters": [],
                        "sort": None,
                        "is_follow_up": False,
                        "clarification_question": (
                            "What Salesforce data would you like to analyze?"
                        ),
                    }
                },
                validation_status="needs_clarification",
            )

        normalized = self._normalize(question)

        intent_name = self._detect_intent(normalized)
        metrics = self._detect_metrics(normalized)
        group_by = self._detect_groupings(normalized)
        filters = self._extract_basic_filters(normalized)
        sort = self._detect_sort(normalized)

        is_follow_up = self._detect_follow_up(normalized, context)

        intent = {
            "intent": intent_name,
            "original_question": question,
            "entities": self._detect_entities(intent_name),
            "metrics": metrics,
            "group_by": group_by,
            "filters": filters,
            "sort": sort,
            "is_follow_up": is_follow_up,
            "clarification_question": None,
        }

        context.intent = intent

        return self._result(
            context=context,
            status="success",
            output={"intent": intent},
            validation_status="passed",
        )

    @staticmethod
    def _get_question(context: AgentContext) -> str:
        """
        Read the question from the request context.

        Adjust the candidate field names to match AgentContext in base.py.
        """
        for field in ("user_question", "question", "message", "query"):
            value = getattr(context, field, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    @staticmethod
    def _normalize(question: str) -> str:
        return re.sub(r"\s+", " ", question.lower()).strip()

    def _detect_intent(self, question: str) -> str:
        # Prefer more specific intents over broad sales analysis.
        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["owner_performance"]
        ):
            return "owner_performance"

        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["quota_analysis"]
        ):
            return "quota_analysis"

        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["lead_analysis"]
        ):
            return "lead_analysis"

        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["account_analysis"]
        ):
            return "account_analysis"

        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["sales_by_region"]
        ):
            return "sales_by_region"

        if any(
            phrase in question
            for phrase in self.INTENT_KEYWORDS["sales_analysis"]
        ):
            return "sales_analysis"

        return "unknown"

    def _detect_metrics(self, question: str) -> list[str]:
        metrics = []

        for metric, keywords in self.METRIC_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                metrics.append(metric)

        # Common implicit metric in ranking and grouping requests.
        if not metrics and any(
            word in question
            for word in ("top", "highest", "lowest", "by region", "by owner")
        ):
            metrics.append("count")

        return metrics

    def _detect_groupings(self, question: str) -> list[str]:
        group_by = []

        for dimension, keywords in self.GROUPING_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                group_by.append(dimension)

        return group_by

    @staticmethod
    def _extract_basic_filters(question: str) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []

        # Extract common Salesforce opportunity stages.
        if "closed won" in question:
            filters.append({
                "field": "StageName",
                "operator": "=",
                "value": "Closed Won",
            })

        if "closed lost" in question:
            filters.append({
                "field": "StageName",
                "operator": "=",
                "value": "Closed Lost",
            })

        # Extract common lead ratings.
        if re.search(r"\bhot\b", question):
            filters.append({
                "field": "Rating",
                "operator": "=",
                "value": "Hot",
            })

        if re.search(r"\bwarm\b", question):
            filters.append({
                "field": "Rating",
                "operator": "=",
                "value": "Warm",
            })

        if "unconverted" in question:
            filters.append({
                "field": "IsConverted",
                "operator": "=",
                "value": False,
            })

        # Extract a simple relative date range, e.g. "last 90 days".
        date_match = re.search(
            r"\blast\s+(\d+)\s+days?\b",
            question,
        )
        if date_match:
            filters.append({
                "field": "CreatedDate",
                "operator": ">=",
                "value": {
                    "type": "relative_date",
                    "days": int(date_match.group(1)),
                },
            })

        return filters

    @staticmethod
    def _detect_sort(question: str) -> dict[str, str] | None:
        if any(
            phrase in question
            for phrase in (
                "highest to lowest",
                "descending",
                "descending order",
                "most to least",
            )
        ):
            return {"direction": "DESC"}

        if any(
            phrase in question
            for phrase in (
                "lowest to highest",
                "ascending",
                "ascending order",
                "least to most",
            )
        ):
            return {"direction": "ASC"}

        return None

    @staticmethod
    def _detect_entities(intent_name: str) -> list[str]:
        mapping = {
            "sales_by_region": ["Opportunity", "Account"],
            "sales_analysis": ["Opportunity"],
            "lead_analysis": ["Lead"],
            "account_analysis": ["Account"],
            "quota_analysis": ["Quota__c", "User"],
            "owner_performance": ["Opportunity", "User"],
        }
        return mapping.get(intent_name, [])

    @staticmethod
    def _detect_follow_up(
        question: str,
        context: AgentContext,
    ) -> bool:
        follow_up_phrases = (
            "show me more",
            "break it down",
            "drill down",
            "same data",
            "change the chart",
            "instead",
            "what about",
            "now show",
            "filter further",
            "also show",
        )

        history = getattr(context, "conversation_history", None)
        if history is None:
            history = getattr(context, "messages", None)

        has_history = bool(history)

        return has_history and any(
            phrase in question for phrase in follow_up_phrases
        )

    def _result(
        self,
        context: AgentContext,
        status: str,
        output: dict[str, Any],
        validation_status: str,
    ) -> AgentResult:
        return AgentResult(
            status=status,
            output=output,
            provenance=AgentProvenance(
                agent_name=self.name,
                input_request_id=context.request_id,
                source_refs=("user_question",),
            ),
            validation_status=validation_status,
        )