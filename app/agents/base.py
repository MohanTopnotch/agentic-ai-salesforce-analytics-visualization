from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class AgentContext:
    request_id: str
    session_id: str | None
    user_id: str | None
    role: str | None
    question: str
    conversation_history: tuple[dict[str, str], ...] = ()
    state: dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

class BaseAgent(ABC):
    name: str
    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
