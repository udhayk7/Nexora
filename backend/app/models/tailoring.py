import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import Resume, ResumeVersion
    from app.models.user import User


class ResumeTailoringSession(Base, TimestampMixin):
    """
    Tracks an interactive job-specific resume tailoring workspace session
    scoped to an authenticated user, base resume version, and target job.
    """

    __tablename__ = "resume_tailoring_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="created",
        nullable=False,
        index=True,
    )
    job_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    latex_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    tailored_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="tailoring_sessions",
    )
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="tailoring_sessions",
    )
    version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        foreign_keys=[version_id],
        back_populates="tailoring_sessions",
    )
    tailored_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
        foreign_keys=[tailored_version_id],
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="tailoring_sessions",
    )
    changes: Mapped[list["ResumeTailoringChange"]] = relationship(
        "ResumeTailoringChange",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="asc(ResumeTailoringChange.order_index)",
    )


class ResumeTailoringChange(Base, TimestampMixin):
    """
    Individual AI-proposed or user-modified structured change.
    Every change is traceable to supporting evidence in the original resume.
    """

    __tablename__ = "resume_tailoring_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_tailoring_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    section_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    change_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    original_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    proposed_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    user_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    supporting_evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    related_job_requirement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence_level: Mapped[str] = mapped_column(
        String(20),
        default="high",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    session: Mapped["ResumeTailoringSession"] = relationship(
        "ResumeTailoringSession",
        back_populates="changes",
    )
