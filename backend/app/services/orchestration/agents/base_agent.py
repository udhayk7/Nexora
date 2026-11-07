from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.orchestration.candidate_context import SharedCandidateContext


@dataclass
class AgentResult:
    """Structured result returned by a specialized AI agent."""

    agent_name: str
    operation: str
    status: str = "completed"  # "completed", "failed", "requires_approval"
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    action_proposals: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    tokens_used: int = 0
    provider: str = "deterministic"
    requires_approval: bool = False
    error_message: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all specialized AI career intelligence agents."""

    name: str = "base_agent"
    description: str = "Base agent"

    @abstractmethod
    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        """Executes agent-specific career analysis, retrieval, or preparation."""
        raise NotImplementedError
