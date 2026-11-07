import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume import Resume, ResumeVersion
    from app.models.user import User


class JobIntelligence(Base, TimestampMixin):
    """Structured, evidence-grounded intelligence extracted from a job description.

    Shared across users for the same job requisition; does NOT contain any private resume data.
    """

    __tablename__ = "job_intelligences"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        default="deterministic",
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(50),
        default="v1.0",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    required_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    experience_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    educational_qualifications: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    responsibilities: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    tools_and_frameworks: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    seniority_level: Mapped[str] = mapped_column(
        String(50),
        default="fresher",
        nullable=False,
    )
    work_arrangement: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        nullable=False,
    )
    compensation_info: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    application_requirements: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    evidence_excerpts: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    is_deterministic_fallback: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="intelligence",
    )
    ai_matches: Mapped[list["AIJobMatch"]] = relationship(
        "AIJobMatch",
        back_populates="job_intelligence",
        cascade="all, delete-orphan",
    )


class AIJobMatch(Base, TimestampMixin):
    """Personalized AI-assisted assessment between a specific resume version and a job requisition.

    Scoped strictly to user_id. Preserves evidence citations, fit reasoning, and skill gaps.
    """

    __tablename__ = "ai_job_matches"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "resume_version_id",
            "job_id",
            name="uq_user_resume_version_job_ai",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_intelligence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_intelligences.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    assessment_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    compatibility_rating: Mapped[str] = mapped_column(
        String(50),
        default="moderate",
        nullable=False,
        index=True,
    )
    fit_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    fit_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    strengths: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    skill_gaps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    experience_alignment: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    transferable_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    missing_requirements: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    recommendation_rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    next_steps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    evidence_citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        default="deterministic",
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(50),
        default="v1.0",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="completed",
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_deterministic_fallback: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="ai_job_matches",
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="ai_matches",
    )
    resume: Mapped["Resume"] = relationship(
        "Resume",
    )
    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
    )
    job_intelligence: Mapped[Optional["JobIntelligence"]] = relationship(
        "JobIntelligence",
        back_populates="ai_matches",
    )
