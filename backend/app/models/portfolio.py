"""
Portfolio Studio & Professional Showcase Models.
Provides structured storage for career portfolios, projects, sections, versions, and analytics.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Portfolio(Base, TimestampMixin):
    """
    Core Portfolio model owned by a user.
    Maintains public slug, publication status, selected template, and profile data.
    """

    __tablename__ = "portfolios"

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
    public_slug: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Professional Career Portfolio",
    )
    headline: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    template_id: Mapped[str] = mapped_column(
        String(32),
        default="minimal",
        nullable=False,
    )  # minimal, developer, ai_tech
    theme_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=lambda: {
            "accent_color": "#3B82F6",
            "font_family": "inter",
            "dark_mode": "system",
            "show_contact_form": False,
            "show_view_counter": True,
        },
        nullable=False,
    )
    profile_data: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=lambda: {
            "full_name": "",
            "headline": "",
            "avatar_url": None,
            "summary": "",
            "location": "",
            "target_roles": [],
            "technical_skills": [],
            "contact_email": None,
            "phone": None,
            "github_url": None,
            "linkedin_url": None,
            "website_url": None,
            "education": [],
            "work_experience": [],
            "certifications": [],
            "achievements": [],
        },
        nullable=False,
    )
    custom_css: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore # noqa: F821
        "User",
        back_populates="portfolio",
    )
    sections: Mapped[list["PortfolioSection"]] = relationship(
        "PortfolioSection",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioSection.order_index",
    )
    projects: Mapped[list["PortfolioProject"]] = relationship(
        "PortfolioProject",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioProject.order_index",
    )
    versions: Mapped[list["PortfolioVersion"]] = relationship(
        "PortfolioVersion",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioVersion.version_number.desc()",
    )
    events: Mapped[list["PortfolioViewEvent"]] = relationship(
        "PortfolioViewEvent",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )


class PortfolioSection(Base, TimestampMixin):
    """
    Configurable section within a portfolio.
    Allows reordering and toggling visibility.
    """

    __tablename__ = "portfolio_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    section_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # about, experience, projects, skills, education, certifications, achievements, contact
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    content_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Relationship
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="sections",
    )


class PortfolioProject(Base, TimestampMixin):
    """
    Showcase project included in candidate's portfolio.
    Can be imported from learning_projects or created directly.
    """

    __tablename__ = "portfolio_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    learning_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("learning_projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    problem_statement: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tech_stack: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    key_features: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    architecture_overview: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    candidate_contribution: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    repository_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    live_demo_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    image_urls: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    challenges: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    outcomes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="completed",
        nullable=False,
    )  # completed, in_progress, planning
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="projects",
    )
    learning_project: Mapped[Optional["LearningProject"]] = relationship(  # type: ignore # noqa: F821
        "LearningProject",
        back_populates="portfolio_projects",
    )


class PortfolioVersion(Base):
    """
    Immutable snapshot of portfolio state for version history and restore capabilities.
    """

    __tablename__ = "portfolio_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    change_summary: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="versions",
    )


class PortfolioViewEvent(Base):
    """
    Privacy-conscious event tracking for published portfolios.
    Tracks view counts, project views, and export downloads without personal data.
    """

    __tablename__ = "portfolio_view_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # page_view, project_view, pdf_download, html_download
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("portfolio_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    referrer_category: Mapped[str] = mapped_column(
        String(32),
        default="direct",
        nullable=False,
    )  # direct, linkedin, github, search, professional, other
    user_agent_category: Mapped[str] = mapped_column(
        String(32),
        default="desktop",
        nullable=False,
    )  # desktop, mobile, tablet, bot
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    # Relationship
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="events",
    )
