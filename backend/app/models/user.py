import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis
    from app.models.application import JobApplication
    from app.models.company import Company
    from app.models.job import Job
    from app.models.match import JobMatch, UserMatchingPreference
    from app.models.resume import Resume
    from app.models.tailoring import ResumeTailoringSession
    from app.models.token import RefreshToken


class User(Base, TimestampMixin):
    """User account entity."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_companies: Mapped[list["Company"]] = relationship(
        "Company",
        foreign_keys="Company.created_by_user_id",
        back_populates="created_by",
    )
    created_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        foreign_keys="Job.created_by_user_id",
        back_populates="created_by",
    )
    matching_preferences: Mapped[Optional["UserMatchingPreference"]] = relationship(
        "UserMatchingPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    job_matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tailoring_sessions: Mapped[list["ResumeTailoringSession"]] = relationship(
        "ResumeTailoringSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="user",
        cascade="all, delete-orphan",
    )

