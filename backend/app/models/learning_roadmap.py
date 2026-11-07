import uuid
from datetime import datetime, timezone
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
    from app.models.user import User


class LearningRoadmap(Base, TimestampMixin):
    """
    Personalized learning roadmap generated for a target career track or specific technical skills.
    Adapts to candidate's demonstrated resume skills to avoid redundant learning.
    """

    __tablename__ = "learning_roadmaps"

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
    target_role: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    target_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
        index=True,
    )  # active, paused, completed, archived
    difficulty_level: Mapped[str] = mapped_column(
        String(32),
        default="intermediate",
        nullable=False,
    )  # beginner, intermediate, advanced, custom
    total_estimated_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completed_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completion_percentage: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    prerequisites: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    already_mastered_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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
        back_populates="learning_roadmaps",
    )
    milestones: Mapped[list["LearningMilestone"]] = relationship(
        "LearningMilestone",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="LearningMilestone.order_index",
    )
    projects: Mapped[list["LearningProject"]] = relationship(
        "LearningProject",
        back_populates="roadmap",
    )
    activities: Mapped[list["LearningActivity"]] = relationship(
        "LearningActivity",
        back_populates="roadmap",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_learning_roadmaps_user_status", "user_id", "status"),
        Index("ix_learning_roadmaps_user_role", "user_id", "target_role"),
    )


class LearningMilestone(Base, TimestampMixin):
    """
    Stage milestone within a learning roadmap (Beginner, Intermediate, Advanced, Portfolio).
    Contains practical exercises, objectives, and progress tracking.
    """

    __tablename__ = "learning_milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_roadmaps.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # beginner, intermediate, advanced, portfolio
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    learning_objectives: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    practical_exercises: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="not_started",
        nullable=False,
        index=True,
    )  # not_started, in_progress, completed, skipped
    estimated_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    completed_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completion_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationship
    roadmap: Mapped["LearningRoadmap"] = relationship(
        "LearningRoadmap",
        back_populates="milestones",
    )


class LearningResource(Base, TimestampMixin):
    """
    Curated public educational resource or candidate-submitted learning bookmark.
    Preserves verified URLs and distinguishes verified from user suggestions.
    """

    __tablename__ = "learning_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    skill: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )  # e.g., Python Official Docs, MDN, FreeCodeCamp, FastAPI Docs, React Docs
    url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    cost_tier: Mapped[str] = mapped_column(
        String(32),
        default="free",
        nullable=False,
    )  # free, paid, freemium
    resource_type: Mapped[str] = mapped_column(
        String(32),
        default="documentation",
        nullable=False,
    )  # documentation, interactive_course, video_series, tutorial, book, project_guide
    difficulty: Mapped[str] = mapped_column(
        String(32),
        default="beginner",
        nullable=False,
    )  # beginner, intermediate, advanced
    estimated_hours: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_curated: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )  # NULL = global curated catalog; non-null = user-added bookmark

    __table_args__ = (
        Index("ix_learning_resources_skill_diff", "skill", "difficulty"),
        Index("ix_learning_resources_user_curated", "user_id", "is_curated"),
    )


class LearningProject(Base, TimestampMixin):
    """
    Hands-on practical project to demonstrate acquired skills.
    Can be linked to resume evidence only upon explicit candidate verification and details.
    """

    __tablename__ = "learning_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    roadmap_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("learning_roadmaps.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    objective: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tech_stack: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    target_skills: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    functional_requirements: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    suggested_milestones: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="planned",
        nullable=False,
        index=True,
    )  # planned, in_progress, completed, abandoned
    repository_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    live_demo_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    architecture_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    evidence_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    portfolio_ready: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="learning_projects",
    )
    roadmap: Mapped[Optional["LearningRoadmap"]] = relationship(
        "LearningRoadmap",
        back_populates="projects",
    )

    __table_args__ = (Index("ix_learning_projects_user_status", "user_id", "status"),)


class LearningActivity(Base):
    """
    Timestamped study and practice activity log.
    Tracks learning hours, activity types, and notes without mutating resume state.
    """

    __tablename__ = "learning_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    roadmap_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("learning_roadmaps.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("learning_milestones.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("learning_projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    skill: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(
        String(32),
        default="practice",
        nullable=False,
    )  # reading, coding, exercise, project_work, review
    hours_spent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    roadmap: Mapped[Optional["LearningRoadmap"]] = relationship(
        "LearningRoadmap",
        back_populates="activities",
    )

    __table_args__ = (
        Index("ix_learning_activities_user_created", "user_id", "created_at"),
        Index("ix_learning_activities_user_skill", "user_id", "skill"),
    )
