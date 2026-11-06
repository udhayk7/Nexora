import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis
    from app.models.job import Job
    from app.models.match import JobMatch
    from app.models.tailoring import ResumeTailoringSession
    from app.models.user import User


class Resume(Base, TimestampMixin):
    """Resume container entity scoped to an authenticated user."""

    __tablename__ = "resumes"

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
        nullable=False,
    )
    current_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="resumes",
    )
    versions: Mapped[list["ResumeVersion"]] = relationship(
        "ResumeVersion",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="desc(ResumeVersion.version_number)",
    )
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="desc(ResumeAnalysis.created_at)",
    )
    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="resume",
        cascade="all, delete-orphan",
    )
    tailoring_sessions: Mapped[list["ResumeTailoringSession"]] = relationship(
        "ResumeTailoringSession",
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeVersion(Base, TimestampMixin):
    """Immutable version of an uploaded and parsed resume."""

    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    parsing_status: Mapped[str] = mapped_column(
        String(20),
        default="uploaded",
        nullable=False,
    )
    parsed_content: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    raw_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    # Tailored resume metadata and parent lineage
    parent_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tailoring_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True,
        index=True,
    )
    is_tailored: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    latex_source: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    pdf_storage_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    tailoring_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Relationships
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="versions",
    )
    parent_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
        remote_side="ResumeVersion.id",
    )
    job: Mapped[Optional["Job"]] = relationship(
        "Job",
    )
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(
        "ResumeAnalysis",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="desc(ResumeAnalysis.created_at)",
    )
    matches: Mapped[list["JobMatch"]] = relationship(
        "JobMatch",
        back_populates="version",
        cascade="all, delete-orphan",
    )
    tailoring_sessions: Mapped[list["ResumeTailoringSession"]] = relationship(
        "ResumeTailoringSession",
        foreign_keys="[ResumeTailoringSession.version_id]",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version_number"),
    )

