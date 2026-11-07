import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import JobApplication
    from app.models.company import Company
    from app.models.job import Job
    from app.models.resume import ResumeVersion
    from app.models.user import User


class InterviewPreparationSession(Base, TimestampMixin):
    """
    Dedicated interview preparation & mock coaching session.
    Links candidate resume, target job/company, stage, preparation plan, and performance.
    """

    __tablename__ = "interview_preparation_sessions"

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
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    interview_type: Mapped[str] = mapped_column(
        String(50),
        default="mock_interview",
        nullable=False,
        index=True,
        # mock_interview, project_deep_dive, technical_revision, behavioral_prep
    )
    interview_round: Mapped[str] = mapped_column(
        String(50),
        default="technical",
        nullable=False,
        # screening, technical, coding, system_design, behavioral, managerial, final_round
    )
    difficulty: Mapped[str] = mapped_column(
        String(30),
        default="intermediate",
        nullable=False,
        # beginner, intermediate, advanced
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="technical",
        nullable=False,
        # technical, coding_problem_solving, backend_python, frontend_fullstack,
        # ai_ml_genai, database_sql, system_design, project_deep_dive,
        # internship_experience, behavioral_hr
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="in_progress",
        nullable=False,
        index=True,
        # in_progress, completed, abandoned
    )

    # Structured preparation plan (grounded topics, projects, gaps, behavioral)
    preparation_plan: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )

    # User instructions & preferences
    user_instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Progress & Scoring
    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completed_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    average_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # AI Provider & Model provenance
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
    user: Mapped["User"] = relationship("User", back_populates="interview_sessions")
    job: Mapped[Optional["Job"]] = relationship("Job")
    company: Mapped[Optional["Company"]] = relationship("Company")
    application: Mapped[Optional["JobApplication"]] = relationship("JobApplication")
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship("ResumeVersion")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.question_order",
    )
    answers: Mapped[list["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    evaluations: Mapped[list["InterviewEvaluation"]] = relationship(
        "InterviewEvaluation",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list["InterviewPreparationNote"]] = relationship(
        "InterviewPreparationNote",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_interview_sessions_user_status", "user_id", "status"),
        Index("ix_interview_sessions_user_created", "user_id", "created_at"),
    )


class InterviewQuestion(Base, TimestampMixin):
    """
    Individual interview question generated for a preparation session.
    """

    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_preparation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    context_hint: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    expected_points: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    evaluation_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    ideal_answer_outline: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    project_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    session: Mapped["InterviewPreparationSession"] = relationship(
        "InterviewPreparationSession",
        back_populates="questions",
    )
    answers: Mapped[list["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_interview_questions_session_order", "session_id", "question_order"),
    )


class InterviewAnswer(Base, TimestampMixin):
    """
    Candidate answer submitted for an interview question.
    """

    __tablename__ = "interview_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_preparation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    submitted_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    submitted_language: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    session: Mapped["InterviewPreparationSession"] = relationship(
        "InterviewPreparationSession",
        back_populates="answers",
    )
    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion",
        back_populates="answers",
    )
    evaluation: Mapped[Optional["InterviewEvaluation"]] = relationship(
        "InterviewEvaluation",
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_interview_answers_user_session", "user_id", "session_id"),)


class InterviewEvaluation(Base, TimestampMixin):
    """
    AI evaluation of a candidate's submitted answer.
    Provides multi-dimensional rubric scoring, strengths, gaps, and improvements.
    """

    __tablename__ = "interview_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_answers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interview_preparation_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Rubric scores (0.0 to 100.0)
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    technical_correctness_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completeness_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    clarity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    approach_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    communication_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Qualitative Feedback
    strengths: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    missing_points: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    suggested_improvements: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    stronger_answer_example: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evaluation_feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Provenance
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
    answer: Mapped["InterviewAnswer"] = relationship(
        "InterviewAnswer",
        back_populates="evaluation",
    )
    session: Mapped["InterviewPreparationSession"] = relationship(
        "InterviewPreparationSession",
        back_populates="evaluations",
    )


class InterviewPreparationNote(Base, TimestampMixin):
    """
    User-saved notes, revision topics, company research, and personal checklists.
    """

    __tablename__ = "interview_preparation_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("interview_preparation_sessions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    note_type: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
        index=True,
        # topics_to_revise, questions_to_ask, company_research, checklist, general
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interview_notes")
    session: Mapped[Optional["InterviewPreparationSession"]] = relationship(
        "InterviewPreparationSession",
        back_populates="notes",
    )
    application: Mapped[Optional["JobApplication"]] = relationship("JobApplication")
    job: Mapped[Optional["Job"]] = relationship("Job")

    __table_args__ = (Index("ix_interview_notes_user_type", "user_id", "note_type"),)
