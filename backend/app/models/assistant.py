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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import JobApplication
    from app.models.job import Job
    from app.models.resume import Resume, ResumeVersion
    from app.models.user import User


class GmailConnection(Base, TimestampMixin):
    """Encrypted Gmail OAuth connection record for an authenticated Nexora user.

    Stores OAuth tokens encrypted at rest. Never exposes secrets or tokens to API clients.
    """

    __tablename__ = "gmail_connections"

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
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    token_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scopes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="gmail_connection",
    )


class ApplicationPreparation(Base, TimestampMixin):
    """Preparation workspace session for a target job opportunity.

    Tracks checklist milestones, resume alignment, question-answering, and external portal status.
    """

    __tablename__ = "application_preparations"

    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job_preparation"),)

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
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
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
    checklist_status: Mapped[str] = mapped_column(
        String(50),
        default="not_started",
        nullable=False,
        index=True,
    )
    execution_status: Mapped[str] = mapped_column(
        String(50),
        default="not_started",
        nullable=False,
        index=True,
        # "not_started", "preparation_in_progress", "awaiting_approval",
        # "ready_to_apply", "application_page_opened", "submission_pending_confirmation",
        # "submitted_and_confirmed", "failed", "withdrawn"
    )
    execution_channel: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        # "gmail", "official_portal", "external_form"
    )
    execution_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    checklist_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    qa_answers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    portal_opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    submission_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="application_preparations",
    )
    job: Mapped["Job"] = relationship(
        "Job",
    )
    application: Mapped[Optional["JobApplication"]] = relationship(
        "JobApplication",
    )
    resume: Mapped[Optional["Resume"]] = relationship(
        "Resume",
    )
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(
        "CoverLetter",
        back_populates="preparation",
        cascade="all, delete-orphan",
        order_by="desc(CoverLetter.version_number)",
    )
    emails: Mapped[list["ApplicationEmail"]] = relationship(
        "ApplicationEmail",
        back_populates="preparation",
        cascade="all, delete-orphan",
        order_by="desc(ApplicationEmail.created_at)",
    )


class CoverLetter(Base, TimestampMixin):
    """Job-specific cover letter generated from grounded resume evidence.

    Maintains version history, approvals, and compiled PDF export references.
    """

    __tablename__ = "cover_letters"

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
    preparation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_preparations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="Cover Letter",
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    opening: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    body_paragraphs: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    closing: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    skill_alignment: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    experience_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    user_instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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
    pdf_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_deterministic_fallback: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
    )
    job: Mapped["Job"] = relationship(
        "Job",
    )
    preparation: Mapped[Optional["ApplicationPreparation"]] = relationship(
        "ApplicationPreparation",
        back_populates="cover_letters",
    )
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
    )


class ApplicationEmail(Base, TimestampMixin):
    """Personalized recruiter and application email communications.

    Maintains approval workflows, Gmail draft and send history with explicit confirmations.
    """

    __tablename__ = "application_emails"

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
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    preparation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("application_preparations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    email_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    recipient_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    recipient_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
    )
    approval_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    send_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    gmail_draft_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    gmail_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    include_resume_attachment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    cover_letter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cover_letters.id", ondelete="SET NULL"),
        nullable=True,
    )
    include_cover_letter_attachment: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
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
    )
    job: Mapped[Optional["Job"]] = relationship(
        "Job",
    )
    application: Mapped[Optional["JobApplication"]] = relationship(
        "JobApplication",
    )
    preparation: Mapped[Optional["ApplicationPreparation"]] = relationship(
        "ApplicationPreparation",
        back_populates="emails",
    )
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
    )
    cover_letter: Mapped[Optional["CoverLetter"]] = relationship(
        "CoverLetter",
    )
