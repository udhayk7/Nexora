import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.match import JobMatch
    from app.models.user import User


class Job(Base, TimestampMixin):
    """Job opportunity entity for early-career career navigation and discovery."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    normalized_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    employment_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    seniority_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    work_arrangement: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        nullable=False,
        index=True,
    )
    location_text: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    state_province: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    remote_eligibility_regions: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    skills_tags: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    role_family: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    # Explicitly provided salary fields only - never assumed
    salary_min: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    salary_max: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    salary_currency: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    salary_period: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    job_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    application_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    external_source_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    canonical_url_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    source_published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    job_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="unverified",
        nullable=False,
        index=True,
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
        back_populates="jobs",
    )
    sources: Mapped[list["JobSource"]] = relationship(
        "JobSource",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="desc(JobSource.first_seen_at)",
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        back_populates="created_jobs",
    )
    verification_history: Mapped[list["JobVerification"]] = relationship(
        "JobVerification",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="desc(JobVerification.checked_at)",
    )
    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobSource(Base, TimestampMixin):
    """Provenance citation tracking origin, timestamps, and evidence for a job listing."""

    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    evidence_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
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
        back_populates="sources",
    )


class JobVerification(Base, TimestampMixin):
    """Immutable audit record of a job verification check or evidence review."""

    __tablename__ = "job_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verifier_type: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False,
        index=True,
    )
    verifier_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50),
        default="user_evidence",
        nullable=False,
    )
    evidence_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    evidence_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    observed_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )
    verification_outcome: Mapped[str] = mapped_column(
        String(50),
        default="verified",
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="verification_history",
    )
    verifier_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[verifier_user_id],
    )


