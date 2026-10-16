from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class AgentContext:
    """Shared context passed between analytics agents."""

    request_id: str
    user_question: str = ""

    intent: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    # Salesforce metadata discovered for the current request.
    metadata: dict[str, Any] = field(default_factory=dict)

    # Query execution details.
    soql_query: str | None = None
    raw_records: list[dict[str, Any]] = field(default_factory=list)
    query_results: list[dict[str, Any]] = field(default_factory=list)

    # Optional user identity for authorization.
    user_id: str | None = None
    # Analytical output consumed by downstream agents.
    calculated_data: list[dict[str, Any]] = field(default_factory=list)

    # Verification results from the analysis/auditor agent.
    verification: dict[str, Any] = field(default_factory=dict)

    # Visualization specification produced by VisualizationAgent.
    visualization: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentProvenance:
    """Tracks the origin of an agent result."""

    agent_name: str
    input_request_id: str
    source_refs: tuple[str, ...] = ()


@dataclass
class AgentResult:
    """Standardized output returned by an agent."""

    status: Literal[
        "success",
        "error",
        "needs_clarification",
    ]

    output: dict[str, Any] = field(default_factory=dict)
    provenance: AgentProvenance | None = None
    validation_status: str = "pending"
    error: str | None = None


class BaseAgent(ABC):
    """Abstract base class for all analytics agents."""

    name: str = "base_agent"

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent's processing logic."""
        raise NotImplementedError
