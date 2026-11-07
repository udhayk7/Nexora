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
    from app.models.application import JobApplication
    from app.models.job import Job
    from app.models.user import User


class CareerWorkflowRun(Base, TimestampMixin):
    """Orchestration entity tracking end-to-end career workflow execution.

    Coordinates onboarding, discovery matching, application preparation,
    and application execution with bounded retries, idempotency, and approval gates.
    """

    __tablename__ = "career_workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        # "onboarding", "job_discovery_matching", "application_preparation", "application_execution"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
        # "pending", "running", "completed", "failed", "cancelled", "awaiting_approval"
    )
    target_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_step: Mapped[str] = mapped_column(
        String(100),
        default="initialized",
        nullable=False,
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    step_data: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workflow_runs",
    )
    target_job: Mapped[Optional["Job"]] = relationship(
        "Job",
    )
    target_application: Mapped[Optional["JobApplication"]] = relationship(
        "JobApplication",
    )
    steps: Mapped[list["CareerWorkflowStep"]] = relationship(
        "CareerWorkflowStep",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="CareerWorkflowStep.step_order",
    )


class CareerWorkflowStep(Base, TimestampMixin):
    """Granular execution step within a CareerWorkflowRun."""

    __tablename__ = "career_workflow_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("career_workflow_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    step_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
        # "pending", "running", "completed", "failed", "skipped"
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(
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
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workflow_run: Mapped["CareerWorkflowRun"] = relationship(
        "CareerWorkflowRun",
        back_populates="steps",
    )
