import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis
    from app.models.job import Job
    from app.models.resume import Resume, ResumeVersion
    from app.models.user import User


class UserMatchingPreference(Base, TimestampMixin):
    """User-entered preferences and career criteria for deterministic job matching."""

    __tablename__ = "user_matching_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    target_role_families: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    preferred_locations: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    work_arrangement_preferences: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    min_salary: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    salary_currency: Mapped[Optional[str]] = mapped_column(
        String(10),
        default="INR",
        nullable=True,
    )
    salary_period: Mapped[Optional[str]] = mapped_column(
        String(20),
        default="annual",
        nullable=True,
    )
    seniority_preferences: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    preferred_industries: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    excluded_industries: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    excluded_terms: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    excluded_roles: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    preferred_company_sizes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="matching_preferences",
    )


class JobMatch(Base, TimestampMixin):
    """Persisted match assessment between a candidate resume version and a job listing."""

    __tablename__ = "job_matches"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_id",
            "version_id",
            "engine_version",
            name="uq_user_job_version_engine",
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
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resume_analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(
        String(50),
        default="v1.0-deterministic",
        nullable=False,
        index=True,
    )
    match_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    positive_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    gap_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    is_saved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="job_matches",
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="matches",
    )
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="matches",
    )
    version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="matches",
    )
    analysis: Mapped["ResumeAnalysis"] = relationship(
        "ResumeAnalysis",
    )

