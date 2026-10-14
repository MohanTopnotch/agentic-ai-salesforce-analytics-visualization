
import copy
import re
from typing import Any, ClassVar

from app.agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
)


class QueryUnderstandingAgent(BaseAgent):
    name = "query_understanding"

    INTENT_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "revenue_analysis": [
            "revenue",
            "sales",
            "annual revenue",
            "amount",
            "pipeline value",
        ],
        "lead_analysis": [
            "lead",
            "leads",
            "lead source",
            "converted",
            "unconverted",
        ],
        "opportunity_analysis": [
            "opportunity",
            "opportunities",
            "deal",
            "deals",
            "closed won",
            "closed lost",
        ],
        "account_analysis": [
            "account",
            "accounts",
            "customer",
            "customers",
        ],
        "quota_analysis": [
            "quota",
            "target",
            "attainment",
        ],
    }

    GROUPING_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "Region__c": ["region", "regions", "territory", "territories"],
        "Industry": ["industry", "industries"],
        "OwnerId": ["owner", "owners", "sales rep", "sales representative"],
        "LeadSource": ["lead source", "lead sources", "source"],
        "StageName": ["stage", "stages", "sales stage"],
        "Rating": ["rating", "ratings"],
        "CreatedDate": ["created date", "creation date"],
        "CloseDate": ["close date", "closing date"],
        "AccountId": ["account", "accounts", "customer", "customers"],
    }

    METRIC_KEYWORDS: ClassVar[dict[str, list[str]]] = {
        "revenue": [
            "revenue",
            "sales amount",
            "annual revenue",
            "pipeline value",
        ],
        "count": [
            "count",
            "number of",
            "how many",
            "total leads",
            "total accounts",
            "total opportunities",
        ],
        "average_revenue": [
            "average revenue",
            "average sales",
            "mean revenue",
        ],
    }

    FOLLOW_UP_PHRASES: ClassVar[list[str]] = [
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
        "show only",
        "top ",
        "sort by",
        "order by",
        "descending",
        "ascending",
        "only show",
        "exclude",
        "include",
        "for the same",
        "same results",
        "and group by",
        "group it by",
    ]

    def run(self, context: AgentContext) -> AgentResult:
        question = self._get_question(context)

        if not question:
            return self._result(
                status="needs_clarification",
                output={
                    "clarification_question": (
                        "What Salesforce data would you like to analyze?"
                    )
                },
                message="A question is required.",
            )

        normalized = self._normalize(question)
        prior_intent = self._get_prior_intent(context)
        is_follow_up = self._detect_follow_up(normalized, context)

        # A follow-up requires an earlier intent to inherit.
        if is_follow_up and not prior_intent:
            return self._result(
                status="needs_clarification",
                output={
                    "clarification_question": (
                        "Which previous analysis should I refine? "
                        "Please restate the metric or analysis."
                    )
                },
                message="No previous analysis is available for this follow-up.",
            )

        detected_intent = self._detect_intent(normalized)
        detected_metrics = self._detect_metrics(normalized)
        detected_group_by = self._detect_group_by(normalized)
        detected_filters = self._extract_basic_filters(normalized)
        detected_sort = self._detect_sort(normalized)
        detected_limit = self._detect_limit(normalized)

        if is_follow_up and prior_intent:
            intent = self._merge_follow_up(
                question=question,
                prior_intent=prior_intent,
                detected_intent=detected_intent,
                detected_metrics=detected_metrics,
                detected_group_by=detected_group_by,
                detected_filters=detected_filters,
                detected_sort=detected_sort,
                detected_limit=detected_limit,
            )
        else:
            intent = {
                "intent": detected_intent,
                "original_question": question,
                "entities": self._extract_entities(normalized),
                "metrics": detected_metrics or ["count"],
                "group_by": detected_group_by,
                "filters": detected_filters,
                "sort": detected_sort,
                "limit": detected_limit,
                "is_follow_up": False,
                "clarification_question": None,
            }

        context.intent = intent

        return self._result(
            status="success",
            output={"intent": intent},
            message="Query intent identified.",
        )

    @staticmethod
    def _get_question(context: AgentContext) -> str:
        question = getattr(context, "user_request", None)

        if not question:
            question = getattr(context, "user_question", None)

        if not question:
            question = getattr(context, "question", None)

        return str(question or "").strip()

    @staticmethod
    def _normalize(question: str) -> str:
        return re.sub(r"\s+", " ", question.strip().lower())

    @staticmethod
    def _get_prior_intent(context: AgentContext) -> dict[str, Any] | None:
        metadata = getattr(context, "metadata", {}) or {}

        prior_intent = metadata.get("prior_intent")
        if isinstance(prior_intent, dict) and prior_intent:
            return copy.deepcopy(prior_intent)

        history = getattr(context, "conversation_history", None) or []

        for message in reversed(history):
            if not isinstance(message, dict):
                continue

            candidate = message.get("intent")
            if isinstance(candidate, dict) and candidate:
                return copy.deepcopy(candidate)

        return None

    def _detect_follow_up(
        self,
        normalized: str,
        context: AgentContext,
    ) -> bool:
        history = getattr(context, "conversation_history", None) or []
        messages = getattr(context, "messages", None) or []
        metadata = getattr(context, "metadata", {}) or {}

        has_previous_context = bool(
            metadata.get("prior_intent") or history or messages
        )

        if not has_previous_context:
            return False

        return any(
            phrase in normalized
            for phrase in self.FOLLOW_UP_PHRASES
        )

    def _detect_intent(self, question: str) -> str:
        for intent_name, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                return intent_name

        return "general_sales_analysis"

    def _detect_metrics(self, question: str) -> list[str]:
        # Check longer, more specific phrases before general ones.
        if any(
            phrase in question
            for phrase in self.METRIC_KEYWORDS["average_revenue"]
        ):
            return ["average_revenue"]

        metrics: list[str] = []

        for metric_name, keywords in self.METRIC_KEYWORDS.items():
            if metric_name == "average_revenue":
                continue

            if any(keyword in question for keyword in keywords):
                metrics.append(metric_name)

        if metrics:
            return list(dict.fromkeys(metrics))

        if any(
            phrase in question
            for phrase in [
                "top ",
                "highest",
                "lowest",
                "by region",
                "by owner",
                "by industry",
            ]
        ):
            return ["count"]

        return []

    def _detect_group_by(self, question: str) -> list[str]:
        group_by: list[str] = []

        for field_name, keywords in self.GROUPING_KEYWORDS.items():
            if any(keyword in question for keyword in keywords):
                group_by.append(field_name)

        return list(dict.fromkeys(group_by))

    def _extract_basic_filters(self, question: str) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []

        if "closed won" in question:
            filters.append(
                {
                    "field": "StageName",
                    "operator": "equals",
                    "value": "Closed Won",
                }
            )
        elif "closed lost" in question:
            filters.append(
                {
                    "field": "StageName",
                    "operator": "equals",
                    "value": "Closed Lost",
                }
            )

        if "hot" in question and "warm" in question:
            filters.append(
                {
                    "field": "Rating",
                    "operator": "in",
                    "value": ["Hot", "Warm"],
                }
            )
        elif re.search(r"\bhot\b", question):
            filters.append(
                {
                    "field": "Rating",
                    "operator": "equals",
                    "value": "Hot",
                }
            )
        elif re.search(r"\bwarm\b", question):
            filters.append(
                {
                    "field": "Rating",
                    "operator": "equals",
                    "value": "Warm",
                }
            )

        if "unconverted" in question or "not converted" in question:
            filters.append(
                {
                    "field": "IsConverted",
                    "operator": "equals",
                    "value": False,
                }
            )
        elif "converted leads" in question:
            filters.append(
                {
                    "field": "IsConverted",
                    "operator": "equals",
                    "value": True,
                }
            )

        relative_date = re.search(
            r"last\s+(\d+)\s+days?",
            question,
        )
        if relative_date:
            filters.append(
                {
                    "field": "CreatedDate",
                    "operator": "relative_date",
                    "value": f"LAST_N_DAYS:{relative_date.group(1)}",
                }
            )

        year_match = re.search(r"\b(20\d{2})\b", question)
        if year_match:
            year = int(year_match.group(1))
            filters.append(
                {
                    "field": "CreatedDate",
                    "operator": "calendar_year",
                    "value": year,
                }
            )

        return filters

    @staticmethod
    def _detect_sort(question: str) -> dict[str, str] | None:
        if not any(
            phrase in question
            for phrase in [
                "sort",
                "order by",
                "highest",
                "lowest",
                "descending",
                "ascending",
            ]
        ):
            return None

        direction = (
            "ASC"
            if any(
                phrase in question
                for phrase in ["ascending", "lowest", "smallest"]
            )
            else "DESC"
        )

        if "count" in question or "number of" in question:
            field = "count"
        elif "amount" in question or "revenue" in question:
            field = "revenue"
        else:
            field = "revenue"

        return {"field": field, "direction": direction}

    @staticmethod
    def _detect_limit(question: str) -> int | None:
        match = re.search(
            r"\btop\s+(\d+)\b|\bfirst\s+(\d+)\b",
            question,
        )

        if not match:
            return None

        value = int(match.group(1) or match.group(2))
        return max(1, min(value, 1000))

    @staticmethod
    def _extract_entities(question: str) -> list[str]:
        entities: list[str] = []

        known_entities = [
            "lead",
            "leads",
            "account",
            "accounts",
            "opportunity",
            "opportunities",
            "revenue",
            "region",
            "owner",
            "industry",
            "quota",
        ]

        for entity in known_entities:
            if re.search(rf"\b{re.escape(entity)}\b", question):
                entities.append(entity)

        return list(dict.fromkeys(entities))

    @staticmethod
    def _merge_follow_up(
        question: str,
        prior_intent: dict[str, Any],
        detected_intent: str,
        detected_metrics: list[str],
        detected_group_by: list[str],
        detected_filters: list[dict[str, Any]],
        detected_sort: dict[str, str] | None,
        detected_limit: int | None,
    ) -> dict[str, Any]:
        merged = copy.deepcopy(prior_intent)

        merged["original_question"] = question
        merged["is_follow_up"] = True
        merged["clarification_question"] = None

        if detected_intent != "general_sales_analysis":
            merged["intent"] = detected_intent

        # Only replace inherited metrics when the new question explicitly
        # identifies a metric.
        if detected_metrics:
            merged["metrics"] = detected_metrics

        # A new grouping replaces the previous grouping.
        if detected_group_by:
            merged["group_by"] = detected_group_by

        # Merge filters by field so a new filter updates the old one.
        filters_by_field: dict[str, dict[str, Any]] = {
            item["field"]: item
            for item in merged.get("filters", [])
            if isinstance(item, dict) and item.get("field")
        }

        for item in detected_filters:
            filters_by_field[item["field"]] = item

        merged["filters"] = list(filters_by_field.values())

        if detected_sort is not None:
            merged["sort"] = detected_sort

        if detected_limit is not None:
            merged["limit"] = detected_limit

        # Preserve prior values when the follow-up does not specify changes.
        merged.setdefault("metrics", ["count"])
        merged.setdefault("group_by", [])
        merged.setdefault("filters", [])
        merged.setdefault("sort", None)
        merged.setdefault("limit", None)
        merged["entities"] = QueryUnderstandingAgent._extract_entities(
            question
        )

        return merged
