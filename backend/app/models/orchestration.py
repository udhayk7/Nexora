import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class CopilotSession(Base, TimestampMixin):
    """Conversational session entity for the AI Career Copilot.

    Maintains conversational history, active candidate context reference,
    and linked agent execution traces across career inquiries.
    """

    __tablename__ = "copilot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="Career Intelligence Session",
        nullable=False,
    )
    session_type: Mapped[str] = mapped_column(
        String(50),
        default="career_strategy",
        nullable=False,
        # "career_strategy", "job_search", "application_prep", "interview_prep", "general"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    context_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="copilot_sessions",
    )
    messages: Mapped[list["CopilotMessage"]] = relationship(
        "CopilotMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CopilotMessage.created_at",
    )
    executions: Mapped[list["AgentExecutionRecord"]] = relationship(
        "AgentExecutionRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AgentExecutionRecord.created_at",
    )


class CopilotMessage(Base, TimestampMixin):
    """Individual interaction message in a Career Copilot conversation.

    Stores candidate prompts, assistant responses, classified intents,
    multi-agent execution traces, and structured action proposals.
    """

    __tablename__ = "copilot_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        # "user", "assistant", "system"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    intent: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        # "career_strategy", "job_discovery_match", "application_prep", etc.
    )
    agent_trace: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    action_proposals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    token_usage: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    session: Mapped["CopilotSession"] = relationship(
        "CopilotSession",
        back_populates="messages",
    )


class AgentExecutionRecord(Base, TimestampMixin):
    """Immutable audit and execution tracking record for specialized AI agents.

    Records workflow IDs, agent names, operations, execution latency,
    token consumption, provider details, and consequential approval states.
    """

    __tablename__ = "agent_execution_records"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("copilot_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        # "resume_intelligence", "job_discovery", "job_matching",
        # "company_intelligence", "application_preparation", "recruiter_networking",
        # "interview_preparation", "career_strategy"
    )
    operation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
        nullable=False,
        # "pending", "running", "completed", "failed", "requires_approval", "approved", "rejected"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        default="deterministic",
        nullable=False,
    )
    model_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    approval_state: Mapped[str] = mapped_column(
        String(30),
        default="none",
        nullable=False,
        # "none", "pending", "approved", "rejected"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    input_context_summary: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    output_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    session: Mapped[Optional["CopilotSession"]] = relationship(
        "CopilotSession",
        back_populates="executions",
    )
