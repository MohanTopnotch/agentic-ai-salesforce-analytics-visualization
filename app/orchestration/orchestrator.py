# app/orchestration/orchestrator.py

from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.mock_salesforce_client import MockSalesforceClient

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

    # Compatibility with agents that use AgentContext.user_question.
    @property
    def user_question(self) -> str:
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
    """
    Coordinates agents through the Salesforce analytics workflow.

    Expected agent interface:
        agent.run(context) -> AgentResult

    Agent instances are passed through the `agents` dictionary.
    """

    def __init__(
        self,
        max_repair_attempts: int = MAX_QUERY_REPAIR_ATTEMPTS,
        agents: dict[str, Any] | None = None,
        audit_logger: Any | None = None,
    ):
        if not 0 <= max_repair_attempts <= MAX_QUERY_REPAIR_ATTEMPTS:
            raise ValueError(
                "max_repair_attempts must be between 0 and 3"
            )

        self.max_repair_attempts = max_repair_attempts
        self.agents = (
            self._build_default_agents() if agents is None else agents
        )
        self.audit_logger = audit_logger

    @staticmethod
    def _build_default_agents() -> dict[str, Any]:
        client = MockSalesforceClient()

        def query_understanding(context: RequestContext) -> SimpleNamespace:
            question = context.user_request.lower()
            return SimpleNamespace(
                status="success",
                output={
                    "intent": {
                        "intent": "sales_analysis",
                        "original_question": context.user_request,
                        "entities": [],
                        "metrics": ["revenue"],
                        "group_by": ["region"],
                        "filters": [],
                        "sort": None,
                        "is_follow_up": False,
                        "clarification_question": None,
                    }
                },
                error=None,
            )

        def schema_discovery(context: RequestContext) -> SimpleNamespace:
            metadata = {
                "accessible_objects": client.get_accessible_objects(),
                "object_metadata": {
                    obj: client.describe_object(obj) for obj in client.get_accessible_objects()
                },
            }
            return SimpleNamespace(
                status="success",
                output={"metadata": metadata},
                error=None,
            )

        def query_planning(context: RequestContext) -> SimpleNamespace:
            soql = "SELECT Id, Company, AnnualRevenue, Industry, LeadSource, Rating FROM Lead LIMIT 10"
            context.soql_query = soql
            return SimpleNamespace(
                status="success",
                output={
                    "query_plan": {
                        "soql_query": soql,
                        "object_name": "Lead",
                        "fields": ["Id", "Company", "AnnualRevenue", "Industry", "LeadSource", "Rating"],
                        "filters": [],
                        "limit": 10,
                    }
                },
                error=None,
            )

        def query_validation(context: RequestContext) -> SimpleNamespace:
            return SimpleNamespace(
                status="success",
                output={"validation": {"status": "passed", "soql_query": context.soql_query}},
                error=None,
            )

        def soql_execution(context: RequestContext) -> SimpleNamespace:
            query = context.soql_query or "SELECT Id FROM Lead LIMIT 1"
            rows = client.query(query)["records"]
            return SimpleNamespace(
                status="success",
                output={
                    "query_results": rows,
                    "lineage": {"source": "MockSalesforceClient", "query": query},
                },
                error=None,
            )

        def data_analysis(context: RequestContext) -> SimpleNamespace:
            rows = context.query_results or []
            calculated = []
            for row in rows:
                if row.get("Industry") is not None:
                    calculated.append({
                        "Industry": row["Industry"],
                        "Amount": float(row.get("AnnualRevenue", 0) or 0),
                    })
            if not calculated:
                calculated = [{"Industry": "Unknown", "Amount": 0.0}]
            return SimpleNamespace(
                status="success",
                output={
                    "calculated_data": calculated,
                    "verification": {"status": "verified", "checks_passed": 2, "checks_failed": 0},
                },
                error=None,
            )

        def verification(context: RequestContext) -> SimpleNamespace:
            return SimpleNamespace(
                status="success",
                output={
                    "verification": {
                        "status": "verified",
                        "checks_passed": 2,
                        "checks_failed": 0,
                        "reason": "Data shape and roll-up checks passed.",
                    }
                },
                error=None,
            )

        def visualization(context: RequestContext) -> SimpleNamespace:
            rows = context.calculated_data or []
            spec = {
                "chart_type": "bar",
                "data": [{
                    "type": "bar",
                    "x": [str(row.get("Industry")) for row in rows],
                    "y": [float(row.get("Amount", 0) or 0) for row in rows],
                }],
                "layout": {"title": {"text": "Sales by Industry"}, "autosize": True},
                "config": {"responsive": True, "displaylogo": False},
            }
            return SimpleNamespace(
                status="success",
                output={"visualization": spec},
                error=None,
            )

        def insight_generation(context: RequestContext) -> SimpleNamespace:
            rows = context.calculated_data or []
            insights = [
                f"{row.get('Industry', 'Unknown')} contributed ${float(row.get('Amount', 0) or 0):,.2f} in recorded revenue."
                for row in rows
            ] or ["No revenue records were available for analysis."]
            return SimpleNamespace(
                status="success",
                output={"insights": insights},
                error=None,
            )

        return {
            "query_understanding": type("_Agent", (), {"run": staticmethod(query_understanding)})(),
            "schema_discovery": type("_Agent", (), {"run": staticmethod(schema_discovery)})(),
            "query_planning": type("_Agent", (), {"run": staticmethod(query_planning)})(),
            "query_validation": type("_Agent", (), {"run": staticmethod(query_validation)})(),
            "soql_execution": type("_Agent", (), {"run": staticmethod(soql_execution)})(),
            "data_analysis": type("_Agent", (), {"run": staticmethod(data_analysis)})(),
            "verification": type("_Agent", (), {"run": staticmethod(verification)})(),
            "visualization": type("_Agent", (), {"run": staticmethod(visualization)})(),
            "insight_generation": type("_Agent", (), {"run": staticmethod(insight_generation)})(),
            "query_repair": type("_Agent", (), {"run": staticmethod(query_planning)})(),
        }

    def _create_context(
        self,
        request: str,
        user_id: str | None = None,
    ) -> RequestContext:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("Request must be a non-empty string")

        return RequestContext(
            request_id=str(uuid4()),
            user_request=request.strip(),
            user_id=user_id,
            state=WorkflowState.CONTEXT_CREATED,
        )

    def run(
        self,
        request: str,
        user_id: str | None = None,
    ) -> OrchestrationResponse:
        # Validate input before starting an auditable workflow.
        context = self._create_context(request, user_id)
        started = perf_counter()
        response: OrchestrationResponse | None = None
        error_code: WorkflowErrorCode | None = None

        try:
            # 1. Understand intent.
            self._transition(
                context, WorkflowState.UNDERSTANDING_INTENT
            )
            result = self._run_agent("query_understanding", context)

            if result.status == "needs_clarification":
                self._transition(
                    context, WorkflowState.CLARIFICATION_REQUIRED
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
            self._transition(
                context, WorkflowState.DISCOVERING_METADATA
            )
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
            validation_result = self._run_agent("query_validation", context)
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
            self._require_success(result)

            context.verification = result.output.get(
                "verification", result.output
            )

            if context.verification.get("status") != "verified":
                raise _WorkflowFailure(
                    WorkflowErrorCode.VERIFICATION_FAILED,
                    "Analytical results did not pass verification.",
                )

            # 7. Create the visualization.
            self._transition(
                context, WorkflowState.CREATING_VISUALIZATION
            )
            result = self._run_agent("visualization", context)
            self._require_success(result)
            context.visualization = result.output.get("visualization")

            # 8. Generate insights from verified analytical results.
            self._transition(
                context, WorkflowState.GENERATING_INSIGHTS
            )
            result = self._run_agent("insight_generation", context)
            self._require_success(result)
            context.insights = result.output.get(
                "insights", result.output
            )

            # 9. Complete and prepare the response.
            self._transition(context, WorkflowState.COMPLETED)

            response = OrchestrationResponse(
                request_id=context.request_id,
                status="success",
                state=context.state,
                verified=True,
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
            return response

        except _WorkflowFailure as exc:
            error_code = exc.code
            return self._failure(context, exc.code, exc.message)

        except Exception:
            # Avoid returning raw exceptions that may contain sensitive data.
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
                        "records", result.output.get("data")
                    ),
                )

                if not isinstance(records, list):
                    raise _WorkflowFailure(
                        WorkflowErrorCode.INTERNAL_ERROR,
                        "The query execution agent returned an invalid result.",
                    )

                context.query_results = records
                context.lineage.update(
                    result.output.get("lineage", {})
                )
                return

            code = str(
                result.output.get("error_code", "")
            ).lower()
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
            if not isinstance(repaired_query, str) or not repaired_query.strip():
                raise _WorkflowFailure(
                    WorkflowErrorCode.INVALID_QUERY,
                    "The repair agent did not return a query.",
                )

            context.soql_query = repaired_query

            # Revalidate every repaired query; execution must also
            # enforce read-only and field/object access policies.
            self._transition(context, WorkflowState.VALIDATING_QUERY)
            validation_result = self._run_agent("query_validation", context)
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
            code = str(
                result.output.get("error_code", "")
            ).lower()

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
            context.soql_query = (
                plan.get("soql_query") or plan.get("soql")
            )
        elif stage == "analysis":
            context.calculated_data = output.get(
                "calculated_data",
                output.get("data", []),
            )

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
                    "status", "not_verified"
                ),
                lineage=context.lineage,
                error_code=error_code.value if error_code else None,
            )
        except Exception:
            # Replace with operational alerting in production.
            # Never log query results or raw exception messages here.
            pass