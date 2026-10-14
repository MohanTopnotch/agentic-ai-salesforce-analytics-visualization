# app/orchestration/orchestrator.py
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from re import search
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.analysis.calculation import safe_sum
from app.analysis.verification import verify_reconciliation
from app.mock_salesforce_client import MockSalesforceClient

logger = logging.getLogger(__name__)

MAX_QUERY_REPAIR_ATTEMPTS = 3


class WorkflowState(str, Enum):
    RECEIVED = "received"
    CONTEXT_CREATED = "context_created"
    UNDERSTANDING_INTENT = "understanding_intent"
    CLARIFICATION_REQUIRED = "clarification_required"
    DISCOVERING_METADATA = "discovering_metadata"
    PLANNING_QUERY = "planning_query"
    VALIDATING_QUERY = "validating_query"
    EXECUTING_QUERY = "executing_query"
    ANALYZING_RESULTS = "analyzing_results"
    VERIFYING_RESULTS = "verifying_results"
    CREATING_VISUALIZATION = "creating_visualization"
    GENERATING_INSIGHTS = "generating_insights"
    AUDITING = "auditing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    INVALID_QUERY = "invalid_query"
    PERMISSION_DENIED = "permission_denied"
    VERIFICATION_FAILED = "verification_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INTERNAL_ERROR = "internal_error"


@dataclass
class RequestContext:
    request_id: str
    user_request: str
    user_id: str | None = None
    state: WorkflowState = WorkflowState.RECEIVED
    repair_attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Task 6: session and conversation context.
    session_id: str | None = None
    conversation_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    # Shared state used by downstream agents.
    intent: dict[str, Any] = field(default_factory=dict)
    query_plan: dict[str, Any] = field(default_factory=dict)
    soql_query: str | None = None
    query_results: list[dict[str, Any]] = field(default_factory=list)
    calculated_data: list[dict[str, Any]] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    visualization: dict[str, Any] | None = None
    insights: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)

    @property
    def user_question(self) -> str:
        """Compatibility with agents that use AgentContext.user_question."""
        return self.user_request


@dataclass
class OrchestrationResponse:
    request_id: str
    status: str
    state: WorkflowState
    data: dict[str, Any] = field(default_factory=dict)
    error_code: WorkflowErrorCode | None = None
    message: str | None = None
    clarification_question: str | None = None
    verified: bool = False


class _WorkflowFailure(Exception):
    def __init__(
        self,
        code: WorkflowErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AnalyticsOrchestrator:
    """Coordinates agents through the Salesforce analytics workflow."""

    def __init__(
        self,
        max_repair_attempts: int = MAX_QUERY_REPAIR_ATTEMPTS,
        agents: dict[str, Any] | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        if not 0 <= max_repair_attempts <= MAX_QUERY_REPAIR_ATTEMPTS:
            raise ValueError("max_repair_attempts must be between 0 and 3")

        self.max_repair_attempts = max_repair_attempts
        self.agents = (
            self._build_default_agents() if agents is None else agents
        )
        self.audit_logger = audit_logger

        # In-memory session store for local development. Use a persistent,
        # access-controlled store (e.g. Redis/database) in production.
        self.sessions: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _build_default_agents() -> dict[str, Any]:
        client = MockSalesforceClient()

        def query_understanding(context: RequestContext) -> SimpleNamespace:
            question = context.user_request
            normalized = question.lower().strip()
            prior_intent = context.metadata.get("prior_intent")

            follow_up_phrases = (
                "show only",
                "only show",
                "sort by",
                "order by",
                "descending",
                "ascending",
                "top ",
                "instead",
                "what about",
                "also show",
                "break it down",
                "drill down",
            )
            has_history = bool(
                prior_intent or context.conversation_history
            )
            is_follow_up = has_history and any(
                phrase in normalized for phrase in follow_up_phrases
            )

            limit_match = search(r"\btop\s+(\d+)\b", normalized)
            limit = (
                max(1, min(int(limit_match.group(1)), 1000))
                if limit_match
                else None
            )

            if is_follow_up and isinstance(prior_intent, dict):
                intent = deepcopy(prior_intent)
                intent["original_question"] = question
                intent["is_follow_up"] = True

                if limit is not None:
                    intent["limit"] = limit

                if "descending" in normalized or "highest" in normalized:
                    intent["sort"] = {
                        "field": "revenue",
                        "direction": "DESC",
                    }
                elif "ascending" in normalized or "lowest" in normalized:
                    intent["sort"] = {
                        "field": "revenue",
                        "direction": "ASC",
                    }

                return SimpleNamespace(
                    status="success",
                    output={"intent": intent},
                    error=None,
                )

            intent = {
                "intent": "sales_analysis",
                "original_question": question,
                "entities": [],
                "metrics": ["revenue"],
                "group_by": ["region"],
                "filters": [],
                "sort": None,
                "limit": limit,
                "is_follow_up": False,
                "clarification_question": None,
            }
            return SimpleNamespace(
                status="success",
                output={"intent": intent},
                error=None,
            )

        def schema_discovery(context: RequestContext) -> SimpleNamespace:
            accessible_objects = client.get_accessible_objects()
            metadata = {
                "accessible_objects": accessible_objects,
                "object_metadata": {
                    obj: client.describe_object(obj)
                    for obj in accessible_objects
                },
            }
            return SimpleNamespace(
                status="success",
                output={"metadata": metadata},
                error=None,
            )

        def query_planning(context: RequestContext) -> SimpleNamespace:
            # This fallback is intentionally a known, fixed mock query.
            # Replace it with the project QueryPlanningAgent to make the
            # SOQL reflect context.intent and follow-up changes dynamically.
            soql = (
                "SELECT Id, Company, AnnualRevenue, Industry, "
                "LeadSource, Rating FROM Lead LIMIT 10"
            )
            context.soql_query = soql
            return SimpleNamespace(
                status="success",
                output={
                    "query_plan": {
                        "soql_query": soql,
                        "object_name": "Lead",
                        "fields": [
                            "Id",
                            "Company",
                            "AnnualRevenue",
                            "Industry",
                            "LeadSource",
                            "Rating",
                        ],
                        "filters": [],
                        "limit": 10,
                    }
                },
                error=None,
            )

        def query_validation(context: RequestContext) -> SimpleNamespace:
            # Production validation should invoke the project's SOQL guard.
            query = context.soql_query or ""
            if not query.strip():
                return SimpleNamespace(
                    status="error",
                    output={
                        "error_code": "invalid_query",
                        "validation": {"status": "failed"},
                    },
                    error="SOQL query is empty.",
                )
            return SimpleNamespace(
                status="success",
                output={
                    "validation": {
                        "status": "passed",
                        "soql_query": query,
                    }
                },
                error=None,
            )

        def soql_execution(context: RequestContext) -> SimpleNamespace:
            query = context.soql_query or "SELECT Id FROM Lead LIMIT 1"
            try:
                rows = client.query(query)["records"]
            except Exception:  # noqa: BLE001
                # Keep provider internals out of the caller response.
                return SimpleNamespace(
                    status="error",
                    output={"error_code": "invalid_query"},
                    error="Mock Salesforce query execution failed.",
                )
            return SimpleNamespace(
                status="success",
                output={
                    "query_results": rows,
                    "lineage": {
                        "source": "MockSalesforceClient",
                        "query": query,
                    },
                },
                error=None,
            )

        def data_analysis(context: RequestContext) -> SimpleNamespace:
            rows = context.query_results or []
            metric = "AnnualRevenue"
            dimension = "Industry"

            if not rows:
                context.calculated_data = []
                context.verification = {
                    "status": "unverified",
                    "checks_passed": 0,
                    "checks_failed": 1,
                    "reconciliation_delta": None,
                    "reason": "No records available for analysis.",
                }
                return SimpleNamespace(
                    status="error",
                    output={
                        "calculated_data": [],
                        "verification": context.verification,
                    },
                    error="No records available for analysis.",
                )

            try:
                grouped: dict[str, list[Decimal]] = {}
                raw_values: list[Decimal] = []

                for row in rows:
                    if metric not in row:
                        raise ValueError(
                            f"Required metric field '{metric}' is missing."
                        )

                    raw_value = row[metric]
                    if raw_value is None or isinstance(raw_value, bool):
                        raise ValueError(
                            f"Invalid metric value for '{metric}'."
                        )

                    value = Decimal(str(raw_value))
                    if not value.is_finite():
                        raise ValueError(
                            f"Non-finite metric value for '{metric}'."
                        )

                    raw_values.append(value)
                    group = str(row.get(dimension) or "Unknown")
                    grouped.setdefault(group, []).append(value)

                grand_total = safe_sum(raw_values)
                calculated = [
                    {
                        dimension: group,
                        metric: safe_sum(values),
                    }
                    for group, values in sorted(grouped.items())
                ]

                reconciliation = verify_reconciliation(
                    [row[metric] for row in calculated],
                    grand_total,
                )
                context.calculated_data = calculated
                context.verification = {
                    **reconciliation,
                    "status": (
                        "verified"
                        if reconciliation.get("status") == "verified"
                        else "unverified"
                    ),
                }

                passed = context.verification["status"] == "verified"
                return SimpleNamespace(
                    status="success" if passed else "error",
                    output={
                        "calculated_data": calculated,
                        "verification": context.verification,
                    },
                    error=(
                        None
                        if passed
                        else "Grouped totals failed reconciliation."
                    ),
                )
            except (
                ValueError,
                TypeError,
                KeyError,
                InvalidOperation,
            ) as exc:
                context.calculated_data = []
                context.verification = {
                    "status": "unverified",
                    "checks_passed": 0,
                    "checks_failed": 1,
                    "reconciliation_delta": None,
                    "reason": f"Analysis validation failed: {exc}",
                }
                return SimpleNamespace(
                    status="error",
                    output={
                        "calculated_data": [],
                        "verification": context.verification,
                    },
                    error="Analysis input validation failed.",
                )

        def verification(context: RequestContext) -> SimpleNamespace:
            rows = context.query_results or []
            calculated = context.calculated_data or []

            try:
                if not rows or not calculated:
                    raise ValueError(
                        "Raw records and grouped results are required."
                    )

                raw_values: list[Decimal] = []
                for row in rows:
                    if "AnnualRevenue" not in row:
                        raise ValueError(
                            "Required raw metric field 'AnnualRevenue' is missing."
                        )
                    value = row["AnnualRevenue"]
                    if value is None or isinstance(value, bool):
                        raise ValueError("Invalid raw metric value.")
                    number = Decimal(str(value))
                    if not number.is_finite():
                        raise ValueError("Non-finite raw metric value.")
                    raw_values.append(number)

                group_totals: list[Decimal] = []
                for row in calculated:
                    if "AnnualRevenue" not in row:
                        raise ValueError(
                            "Required grouped metric field "
                            "'AnnualRevenue' is missing."
                        )
                    value = row["AnnualRevenue"]
                    if value is None or isinstance(value, bool):
                        raise ValueError("Invalid grouped metric value.")
                    number = Decimal(str(value))
                    if not number.is_finite():
                        raise ValueError("Non-finite grouped metric value.")
                    group_totals.append(number)

                result = verify_reconciliation(
                    group_totals,
                    safe_sum(raw_values),
                )
                passed = result.get("status") == "verified"
                context.verification = {
                    **result,
                    "status": "verified" if passed else "unverified",
                    "reason": (
                        "Grouped totals match the raw-record total."
                        if passed
                        else "Grouped totals do not match the raw-record total."
                    ),
                }
            except (
                ValueError,
                TypeError,
                KeyError,
                InvalidOperation,
            ) as exc:
                context.verification = {
                    "status": "unverified",
                    "checks_passed": 0,
                    "checks_failed": 1,
                    "reconciliation_delta": None,
                    "reason": f"Verification failed: {exc}",
                }

            passed = context.verification.get("status") == "verified"
            return SimpleNamespace(
                status="success" if passed else "error",
                output={"verification": context.verification},
                error=(
                    None
                    if passed
                    else "Analytical results did not pass verification."
                ),
            )

        def visualization(context: RequestContext) -> SimpleNamespace:
            rows = context.calculated_data or []
            spec = {
                "chart_type": "bar",
                "data": [
                    {
                        "type": "bar",
                        "x": [
                            str(row.get("Industry", "Unknown"))
                            for row in rows
                        ],
                        "y": [
                            float(row.get("AnnualRevenue", 0) or 0)
                            for row in rows
                        ],
                    }
                ],
                "layout": {
                    "title": {"text": "Sales by Industry"},
                    "autosize": True,
                },
                "config": {
                    "responsive": True,
                    "displaylogo": False,
                },
            }
            return SimpleNamespace(
                status="success",
                output={"visualization": spec},
                error=None,
            )

        def insight_generation(context: RequestContext) -> SimpleNamespace:
            rows = context.calculated_data or []
            insights = [
                (
                    f"{row.get('Industry', 'Unknown')} contributed "
                    f"${float(row.get('AnnualRevenue', 0) or 0):,.2f} "
                    "in recorded revenue."
                )
                for row in rows
            ] or ["No revenue records were available for analysis."]
            return SimpleNamespace(
                status="success",
                output={"insights": insights},
                error=None,
            )

        def wrap(function: Any) -> Any:
            return type(
                "_Agent",
                (),
                {"run": staticmethod(function)},
            )()

        return {
            "query_understanding": wrap(query_understanding),
            "schema_discovery": wrap(schema_discovery),
            "query_planning": wrap(query_planning),
            "query_validation": wrap(query_validation),
            "soql_execution": wrap(soql_execution),
            "data_analysis": wrap(data_analysis),
            "verification": wrap(verification),
            "visualization": wrap(visualization),
            "insight_generation": wrap(insight_generation),
            "query_repair": wrap(query_planning),
        }

    def _create_context(
        self,
        request: str,
        user_id: str | None = None,
        session_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> RequestContext:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("Request must be a non-empty string")

        return RequestContext(
            request_id=str(uuid4()),
            user_request=request.strip(),
            user_id=user_id,
            session_id=session_id,
            conversation_history=list(conversation_history or []),
            state=WorkflowState.CONTEXT_CREATED,
        )

    def run(
        self,
        request: str,
        user_id: str | None = None,
        session_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> OrchestrationResponse:
        # Validate before beginning the auditable workflow.
        context = self._create_context(
            request=request,
            user_id=user_id,
            session_id=session_id,
            conversation_history=conversation_history,
        )
        started = perf_counter()
        response: OrchestrationResponse | None = None
        error_code: WorkflowErrorCode | None = None

        # Scope sessions by user so one user's history cannot be reused
        # by another user who happens to supply the same session ID.
        session_key = (
            f"{user_id or 'anonymous'}:{session_id}"
            if session_id
            else None
        )

        if session_key:
            saved_session = self.sessions.get(session_key, {})
            saved_history = saved_session.get("history", [])
            context.conversation_history = (
                list(saved_history) + context.conversation_history
            )
            prior_intent = saved_session.get("last_intent")
            if isinstance(prior_intent, dict) and prior_intent:
                context.metadata["prior_intent"] = deepcopy(prior_intent)

        try:
            # 1. Understand intent.
            self._transition(context, WorkflowState.UNDERSTANDING_INTENT)
            result = self._run_agent("query_understanding", context)

            if result.status == "needs_clarification":
                self._transition(
                    context,
                    WorkflowState.CLARIFICATION_REQUIRED,
                )
                response = OrchestrationResponse(
                    request_id=context.request_id,
                    status="needs_clarification",
                    state=context.state,
                    data=result.output,
                    clarification_question=(
                        result.output.get("clarification_question")
                        or result.output.get("intent", {}).get(
                            "clarification_question"
                        )
                    ),
                )
                return response

            self._require_success(result)
            self._apply_output(context, result.output, "intent")

            # 2. Discover accessible metadata.
            self._transition(context, WorkflowState.DISCOVERING_METADATA)
            result = self._run_agent("schema_discovery", context)
            self._require_success(result)
            self._apply_output(context, result.output, "metadata")

            # 3. Plan the query.
            self._transition(context, WorkflowState.PLANNING_QUERY)
            result = self._run_agent("query_planning", context)
            self._require_success(result)
            self._apply_output(context, result.output, "query_plan")

            if not context.soql_query:
                raise _WorkflowFailure(
                    WorkflowErrorCode.INVALID_QUERY,
                    "The query planner did not produce a SOQL query.",
                )

            # 4. Validate and execute the query.
            self._transition(context, WorkflowState.VALIDATING_QUERY)
            validation_result = self._run_agent(
                "query_validation",
                context,
            )
            self._require_success(validation_result)

            self._transition(context, WorkflowState.EXECUTING_QUERY)
            self._execute_with_repair(context)

            # 5. Analyze records.
            self._transition(context, WorkflowState.ANALYZING_RESULTS)
            result = self._run_agent("data_analysis", context)
            self._require_success(result)
            self._apply_output(context, result.output, "analysis")

            # 6. Verify calculations before presenting them.
            self._transition(context, WorkflowState.VERIFYING_RESULTS)
            result = self._run_agent("verification", context)
            context.verification = result.output.get(
                "verification",
                result.output,
            )

            if (
                result.status != "success"
                or context.verification.get("status") != "verified"
                or context.verification.get("checks_failed", 1) != 0
                or context.verification.get("reconciliation_delta") is None
            ):
                raise _WorkflowFailure(
                    WorkflowErrorCode.VERIFICATION_FAILED,
                    "Analytical results did not pass verification.",
                )

            # 7. Create the visualization.
            self._transition(
                context,
                WorkflowState.CREATING_VISUALIZATION,
            )
            result = self._run_agent("visualization", context)
            self._require_success(result)
            context.visualization = result.output.get("visualization")

            # 8. Generate insights from verified results.
            self._transition(
                context,
                WorkflowState.GENERATING_INSIGHTS,
            )
            result = self._run_agent("insight_generation", context)
            self._require_success(result)
            context.insights = result.output.get(
                "insights",
                result.output,
            )

            # 9. Complete and prepare the response.
            self._transition(context, WorkflowState.COMPLETED)
            response = OrchestrationResponse(
                request_id=context.request_id,
                status="success",
                state=context.state,
                verified=(
                    context.verification.get("status") == "verified"
                    and context.verification.get("checks_failed", 1) == 0
                    and context.verification.get("reconciliation_delta")
                    is not None
                ),
                data={
                    "intent": context.intent,
                    "metadata": context.metadata,
                    "query_plan": context.query_plan,
                    "query_results": context.query_results,
                    "calculated_data": context.calculated_data,
                    "verification": context.verification,
                    "visualization": context.visualization,
                    "insights": context.insights,
                    "lineage": context.lineage,
                },
            )

            # Task 6: persist successful intent and exchange in this session.
            if session_key:
                saved_session = self.sessions.setdefault(
                    session_key,
                    {"history": [], "last_intent": {}},
                )
                saved_session["last_intent"] = deepcopy(context.intent)
                saved_session["history"].append(
                    {
                        "question": context.user_request,
                        "intent": deepcopy(context.intent),
                        "request_id": context.request_id,
                        "status": "success",
                    }
                )
                saved_session["history"] = saved_session["history"][-50:]

            return response

        except _WorkflowFailure as exc:
            error_code = exc.code
            return self._failure(context, exc.code, exc.message)

        except Exception:  # noqa: BLE001
            # Do not expose raw exceptions or sensitive provider details.
            error_code = WorkflowErrorCode.INTERNAL_ERROR
            return self._failure(
                context,
                WorkflowErrorCode.INTERNAL_ERROR,
                "The analytics workflow failed unexpectedly.",
            )

        finally:
            duration_ms = (perf_counter() - started) * 1000
            self._write_audit(
                context=context,
                duration_ms=duration_ms,
                error_code=error_code,
            )

    def _execute_with_repair(self, context: RequestContext) -> None:
        for attempt in range(self.max_repair_attempts + 1):
            result = self._run_agent("soql_execution", context)

            if result.status == "success":
                records = result.output.get(
                    "query_results",
                    result.output.get(
                        "records",
                        result.output.get("data"),
                    ),
                )
                if not isinstance(records, list):
                    raise _WorkflowFailure(
                        WorkflowErrorCode.INTERNAL_ERROR,
                        "The query execution agent returned an invalid result.",
                    )
                context.query_results = records
                context.lineage.update(result.output.get("lineage", {}))
                return

            code = str(result.output.get("error_code", "")).lower()
            message = result.error or result.output.get("error", "")

            if self._is_permission_error(code):
                raise _WorkflowFailure(
                    WorkflowErrorCode.PERMISSION_DENIED,
                    "Salesforce access was denied.",
                )

            if self._is_provider_error(code):
                raise _WorkflowFailure(
                    WorkflowErrorCode.PROVIDER_UNAVAILABLE,
                    "The Salesforce query provider is unavailable.",
                )

            if (
                attempt >= self.max_repair_attempts
                or not self._is_repairable(code, message)
            ):
                raise _WorkflowFailure(
                    WorkflowErrorCode.INVALID_QUERY,
                    "Query execution failed and cannot be repaired.",
                )

            repair_agent = self.agents.get("query_repair")
            if repair_agent is None:
                raise _WorkflowFailure(
                    WorkflowErrorCode.INVALID_QUERY,
                    "No query repair agent is configured.",
                )

            context.repair_attempts += 1
            context.metadata["query_repair"] = {
                "attempt": context.repair_attempts,
                "error_code": code,
                "error_message": message,
            }

            repair_result = repair_agent.run(context)
            self._require_success(repair_result)
            repaired_query = repair_result.output.get("soql_query")

            if (
                not isinstance(repaired_query, str)
                or not repaired_query.strip()
            ):
                repaired_plan = repair_result.output.get("query_plan", {})
                repaired_query = repaired_plan.get("soql_query")

            if (
                not isinstance(repaired_query, str)
                or not repaired_query.strip()
            ):
                raise _WorkflowFailure(
                    WorkflowErrorCode.INVALID_QUERY,
                    "The repair agent did not return a query.",
                )

            context.soql_query = repaired_query

            # Every repaired query must pass validation before execution.
            self._transition(context, WorkflowState.VALIDATING_QUERY)
            validation_result = self._run_agent(
                "query_validation",
                context,
            )
            self._require_success(validation_result)
            self._transition(context, WorkflowState.EXECUTING_QUERY)

    def _run_agent(self, name: str, context: RequestContext) -> Any:
        agent = self.agents.get(name)
        if agent is None:
            raise _WorkflowFailure(
                WorkflowErrorCode.INTERNAL_ERROR,
                f"Required agent is not configured: {name}.",
            )

        result = agent.run(context)
        if not hasattr(result, "status") or not hasattr(result, "output"):
            raise _WorkflowFailure(
                WorkflowErrorCode.INTERNAL_ERROR,
                f"Agent returned an invalid result: {name}.",
            )
        return result

    @staticmethod
    def _require_success(result: Any) -> None:
        if result.status != "success":
            code = str(result.output.get("error_code", "")).lower()
            if AnalyticsOrchestrator._is_permission_error(code):
                raise _WorkflowFailure(
                    WorkflowErrorCode.PERMISSION_DENIED,
                    "Access was denied by a workflow agent.",
                )
            raise _WorkflowFailure(
                WorkflowErrorCode.INTERNAL_ERROR,
                "A workflow agent could not complete its task.",
            )

    @staticmethod
    def _apply_output(
        context: RequestContext,
        output: dict[str, Any],
        stage: str,
    ) -> None:
        if stage == "intent":
            context.intent = output.get("intent", output)
        elif stage == "metadata":
            context.metadata.update(output.get("metadata", output))
        elif stage == "query_plan":
            plan = output.get("query_plan", output)
            context.query_plan = plan
            context.soql_query = plan.get("soql_query") or plan.get("soql")
        elif stage == "analysis":
            context.calculated_data = output.get(
                "calculated_data",
                output.get("data", []),
            )
            if isinstance(output.get("verification"), dict):
                context.verification = output["verification"]

    @staticmethod
    def _is_permission_error(code: str) -> bool:
        return any(
            marker in code.lower()
            for marker in (
                "permission_denied",
                "access_denied",
                "unauthorized",
                "forbidden",
            )
        )

    @staticmethod
    def _is_provider_error(code: str) -> bool:
        return any(
            marker in code.lower()
            for marker in (
                "provider_unavailable",
                "connection_error",
                "timeout",
            )
        )

    @staticmethod
    def _is_repairable(code: str, message: str) -> bool:
        if AnalyticsOrchestrator._is_permission_error(code):
            return False
        text = f"{code} {message}".lower()
        return any(
            marker in text
            for marker in (
                "syntax",
                "malformed_query",
                "invalid_filter",
                "invalid_field",
                "unknown_field",
                "unexpected token",
                "missing value",
            )
        )

    @staticmethod
    def _transition(
        context: RequestContext,
        state: WorkflowState,
    ) -> None:
        context.state = state

    def _failure(
        self,
        context: RequestContext,
        code: WorkflowErrorCode,
        message: str,
    ) -> OrchestrationResponse:
        self._transition(context, WorkflowState.FAILED)
        return OrchestrationResponse(
            request_id=context.request_id,
            status="error",
            state=context.state,
            error_code=code,
            message=message,
            verified=False,
        )
    def _write_audit(
        self,
        context: RequestContext,
        duration_ms: float,
        error_code: WorkflowErrorCode | None,
    ) -> None:
        if self.audit_logger is None:
            return
        try:
            self.audit_logger.log_run(
                request_id=context.request_id,
                duration_ms=duration_ms,
                state=context.state.value,
                soql_query=context.soql_query,
                verification_status=context.verification.get(
                    "status",
                    "not_verified",
                ),
                lineage=context.lineage,
                error_code=error_code.value if error_code else None,
            )
        except Exception as exc:  # noqa: BLE001
            # Preserve the analytics response if audit logging fails.
            # Log only the exception type, never sensitive details.
            logger.error(
                "Audit logging failed; exception type: %s",
                type(exc).__name__,
            )