import uuid
from datetime import datetime, timezone
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
    from app.models.company import Company
    from app.models.job import Job
    from app.models.resume import Resume, ResumeVersion
    from app.models.user import User


class JobApplication(Base, TimestampMixin):
    """
    Central user-owned job application tracking entity.
    Tracks applications across stages, channels, resumes, deadlines, and contact details.
    """

    __tablename__ = "job_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="interested",
        nullable=False,
        index=True,
    )
    application_channel: Mapped[str] = mapped_column(
        String(50),
        default="official_portal",
        nullable=False,
        index=True,
    )
    application_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recruiter_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    recruiter_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    recruiter_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    next_follow_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    submission_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    link_opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="applications",
    )
    job: Mapped[Optional["Job"]] = relationship(
        "Job",
        back_populates="applications",
    )
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        back_populates="applications",
    )
    resume: Mapped[Optional["Resume"]] = relationship(
        "Resume",
    )
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(ApplicationStatusHistory.changed_at)",
    )
    activities: Mapped[list["ApplicationActivity"]] = relationship(
        "ApplicationActivity",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(ApplicationActivity.created_at)",
    )
    interviews: Mapped[list["ApplicationInterview"]] = relationship(
        "ApplicationInterview",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="asc(ApplicationInterview.scheduled_at)",
    )


class ApplicationStatusHistory(Base, TimestampMixin):
    """
    Immutable audit record of each status transition on a job application.
    Preserves exact timeline without overwriting historical progression.
    """

    __tablename__ = "application_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="status_history",
    )


class ApplicationActivity(Base, TimestampMixin):
    """
    User-facing activity timeline event for an application.
    Supports submissions, status updates, notes, recruiter touches, and follow-ups.
    """

    __tablename__ = "application_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    activity_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="activities",
    )


class ApplicationInterview(Base, TimestampMixin):
    """
    Scheduled or completed interview / assessment round for an application.
    """

    __tablename__ = "application_interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    interview_type: Mapped[str] = mapped_column(
        String(50),
        default="technical",
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    round_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    meeting_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    interviewer_names: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    preparation_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="scheduled",
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
        index=True,
    )
    next_steps: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="interviews",
    )
