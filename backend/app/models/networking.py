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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import JobApplication
    from app.models.company import Company
    from app.models.job import Job
    from app.models.resume import ResumeVersion
    from app.models.user import User


class RecruiterProfile(Base, TimestampMixin):
    """Structured recruiter intelligence profile.

    Can be shared/global when discovered from public official sources, or user-owned
    when added manually. Never fabricates contact information or identities.
    """

    __tablename__ = "recruiter_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    designation: Mapped[str] = mapped_column(
        String(255),
        default="Recruiter",
        nullable=False,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    recruitment_specialization: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    relevant_departments: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    public_profile_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    associated_job_ids: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        default="official_careers_page",
        nullable=False,
        index=True,
        # "official_careers_page", "team_page", "public_announcement",
        # "official_contact_channel", "manual_user_addition", "job_listing"
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="unverified",
        nullable=False,
        index=True,
        # "verified", "inferred", "unverified"
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
        back_populates="recruiters",
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
    crm_relationships: Mapped[list["NetworkingContact"]] = relationship(
        "NetworkingContact",
        back_populates="recruiter",
        cascade="all, delete-orphan",
    )
    outreach_messages: Mapped[list["NetworkingOutreachMessage"]] = relationship(
        "NetworkingOutreachMessage",
        back_populates="recruiter",
        cascade="all, delete-orphan",
    )


class NetworkingContact(Base, TimestampMixin):
    """User-specific relationship record in the Networking CRM.

    Tracks outreach lifecycle, communication history, response states,
    and scheduled follow-ups for a single candidate-recruiter pair.
    """

    __tablename__ = "networking_contacts"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "recruiter_id",
            name="uq_user_recruiter_relationship",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relationship_status: Mapped[str] = mapped_column(
        String(50),
        default="discovered",
        nullable=False,
        index=True,
        # "discovered", "saved", "outreach_prepared", "contacted",
        # "awaiting_response", "responded", "follow_up_required", "connected", "archived"
    )
    contact_source: Mapped[str] = mapped_column(
        String(50),
        default="recruiter_discovery",
        nullable=False,
    )
    initial_contact_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_contact_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_follow_up_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    communication_channel: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        # "linkedin", "email", "portal", "other"
    )
    response_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        # "pending", "positive", "neutral", "declined", "no_response"
    )
    response_received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    networking_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
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
        back_populates="networking_contacts",
    )
    recruiter: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile",
        back_populates="crm_relationships",
    )
    company: Mapped[Optional["Company"]] = relationship(
        "Company",
    )
    job: Mapped[Optional["Job"]] = relationship(
        "Job",
    )
    application: Mapped[Optional["JobApplication"]] = relationship(
        "JobApplication",
    )
    outreach_messages: Mapped[list["NetworkingOutreachMessage"]] = relationship(
        "NetworkingOutreachMessage",
        back_populates="contact_relationship",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["NetworkingActivity"]] = relationship(
        "NetworkingActivity",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(NetworkingActivity.created_at)",
    )


class NetworkingOutreachMessage(Base, TimestampMixin):
    """Personalized outreach communication draft and delivery record.

    Grounded in candidate's verified resume and career goals. Requires
    explicit user approval before dispatch.
    """

    __tablename__ = "networking_outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("networking_contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    message_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        # "linkedin_connection", "recruiter_intro", "job_inquiry",
        # "internship_inquiry", "follow_up", "interview_thank_you", "networking_email"
    )
    channel: Mapped[str] = mapped_column(
        String(50),
        default="linkedin",
        nullable=False,
        # "linkedin", "email"
    )
    tone: Mapped[str] = mapped_column(
        String(50),
        default="professional",
        nullable=False,
        # "professional", "enthusiastic", "concise", "formal"
    )
    subject: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    grounded_claims: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    character_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
        # "draft", "approved", "sent", "discarded"
    )
    approval_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_via_gmail: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    gmail_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
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
    recruiter: Mapped["RecruiterProfile"] = relationship(
        "RecruiterProfile",
        back_populates="outreach_messages",
    )
    contact_relationship: Mapped[Optional["NetworkingContact"]] = relationship(
        "NetworkingContact",
        back_populates="outreach_messages",
    )
    job: Mapped[Optional["Job"]] = relationship(
        "Job",
    )
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship(
        "ResumeVersion",
    )


class NetworkingActivity(Base):
    """Chronological activity log for a networking contact in the CRM."""

    __tablename__ = "networking_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recruiter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("networking_contacts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        # "status_change", "outreach_drafted", "outreach_approved",
        # "message_sent", "response_recorded", "follow_up_scheduled", "note_added"
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    contact: Mapped[Optional["NetworkingContact"]] = relationship(
        "NetworkingContact",
        back_populates="activities",
    )
