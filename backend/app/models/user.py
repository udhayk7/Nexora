import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import ResumeAnalysis
    from app.models.application import JobApplication
    from app.models.assistant import ApplicationPreparation, GmailConnection
    from app.models.company import Company
    from app.models.company_intelligence import CompanyResearchReport
    from app.models.interview_prep import (
        InterviewPreparationNote,
        InterviewPreparationSession,
    )
    from app.models.job import Job
    from app.models.learning_roadmap import LearningProject, LearningRoadmap
    from app.models.match import JobMatch, UserMatchingPreference
    from app.models.notification import Notification, UserNotificationPreference
    from app.models.portfolio import Portfolio
    from app.models.recommendation import AIJobMatch
    from app.models.resume import Resume
    from app.models.tailoring import ResumeTailoringSession
    from app.models.token import RefreshToken
    from app.models.workflow import CareerWorkflowRun


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
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notification_preferences: Mapped[Optional["UserNotificationPreference"]] = relationship(
        "UserNotificationPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ai_job_matches: Mapped[list["AIJobMatch"]] = relationship(
        "AIJobMatch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    gmail_connection: Mapped[Optional["GmailConnection"]] = relationship(
        "GmailConnection",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    application_preparations: Mapped[list["ApplicationPreparation"]] = relationship(
        "ApplicationPreparation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_sessions: Mapped[list["InterviewPreparationSession"]] = relationship(
        "InterviewPreparationSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    interview_notes: Mapped[list["InterviewPreparationNote"]] = relationship(
        "InterviewPreparationNote",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    company_research_reports: Mapped[list["CompanyResearchReport"]] = relationship(
        "CompanyResearchReport",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learning_roadmaps: Mapped[list["LearningRoadmap"]] = relationship(
        "LearningRoadmap",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learning_projects: Mapped[list["LearningProject"]] = relationship(
        "LearningProject",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    portfolio: Mapped[Optional["Portfolio"]] = relationship(
        "Portfolio",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    workflow_runs: Mapped[list["CareerWorkflowRun"]] = relationship(
        "CareerWorkflowRun",
        back_populates="user",
        cascade="all, delete-orphan",
    )
