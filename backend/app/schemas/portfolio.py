"""
Portfolio Studio & Professional Showcase Schemas.
Pydantic validation models for candidate portfolios, sections, projects, and analytics.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class EducationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    highlights: list[str] = Field(default_factory=list)


class WorkExperienceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company: str
    role: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    bullet_points: list[str] = Field(default_factory=list)


class CertificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    issuer: str
    issue_date: Optional[str] = None
    url: Optional[str] = None
    credential_id: Optional[str] = None


class AchievementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    date: Optional[str] = None


class ProfileData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str = ""
    headline: str = ""
    avatar_url: Optional[str] = None
    summary: str = ""
    location: str = ""
    target_roles: list[str] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    education: list[EducationItem] = Field(default_factory=list)
    work_experience: list[WorkExperienceItem] = Field(default_factory=list)
    certifications: list[CertificationItem] = Field(default_factory=list)
    achievements: list[AchievementItem] = Field(default_factory=list)


class ThemeConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    accent_color: str = "#3B82F6"
    font_family: str = "inter"
    dark_mode: str = "system"
    show_contact_form: bool = False
    show_view_counter: bool = True


class PortfolioSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    section_type: str
    title: str
    is_visible: bool
    order_index: int
    content_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class PortfolioSectionUpdate(BaseModel):
    title: Optional[str] = None
    is_visible: Optional[bool] = None
    order_index: Optional[int] = None
    content_json: Optional[dict[str, Any]] = None


class SectionReorderItem(BaseModel):
    id: uuid.UUID
    order_index: int
    is_visible: bool = True


class PortfolioSectionsReorderRequest(BaseModel):
    sections: list[SectionReorderItem]


class PortfolioProjectCreate(BaseModel):
    learning_project_id: Optional[uuid.UUID] = None
    title: str
    problem_statement: Optional[str] = None
    description: str
    tech_stack: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    architecture_overview: Optional[str] = None
    candidate_contribution: Optional[str] = None
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    challenges: Optional[str] = None
    outcomes: Optional[str] = None
    status: str = "completed"
    is_featured: bool = False
    is_visible: bool = True
    order_index: int = 0


class PortfolioProjectUpdate(BaseModel):
    title: Optional[str] = None
    problem_statement: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    key_features: Optional[list[str]] = None
    architecture_overview: Optional[str] = None
    candidate_contribution: Optional[str] = None
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    image_urls: Optional[list[str]] = None
    challenges: Optional[str] = None
    outcomes: Optional[str] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    is_visible: Optional[bool] = None
    order_index: Optional[int] = None


class PortfolioProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    portfolio_id: uuid.UUID
    learning_project_id: Optional[uuid.UUID] = None
    title: str
    problem_statement: Optional[str] = None
    description: str
    tech_stack: list[str]
    key_features: list[str]
    architecture_overview: Optional[str] = None
    candidate_contribution: Optional[str] = None
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    image_urls: list[str]
    challenges: Optional[str] = None
    outcomes: Optional[str] = None
    status: str
    is_featured: bool
    is_visible: bool
    order_index: int
    created_at: datetime
    updated_at: datetime


class PortfolioVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    change_summary: Optional[str] = None
    created_at: datetime


class PortfolioVersionCreate(BaseModel):
    change_summary: Optional[str] = None


class PortfolioProfileUpdate(BaseModel):
    title: Optional[str] = None
    headline: Optional[str] = None
    profile_data: ProfileData


class PortfolioThemeUpdate(BaseModel):
    template_id: Optional[str] = None
    theme_config: ThemeConfig
    custom_css: Optional[str] = None


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    public_slug: str
    title: str
    headline: Optional[str] = None
    is_published: bool
    published_at: Optional[datetime] = None
    template_id: str
    theme_config: dict[str, Any]
    profile_data: dict[str, Any]
    custom_css: Optional[str] = None
    sections: list[PortfolioSectionResponse] = Field(default_factory=list)
    projects: list[PortfolioProjectResponse] = Field(default_factory=list)
    versions_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicPortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_slug: str
    title: str
    headline: Optional[str] = None
    template_id: str
    theme_config: dict[str, Any]
    profile_data: dict[str, Any]
    sections: list[PortfolioSectionResponse]
    projects: list[PortfolioProjectResponse]
    published_at: Optional[datetime] = None


class ViewTrendPoint(BaseModel):
    date: str
    views: int


class ProjectViewStat(BaseModel):
    project_id: Optional[str] = None
    title: str
    views: int


class PortfolioAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_views: int
    project_views: int
    downloads_count: int
    views_by_date: list[ViewTrendPoint] = Field(default_factory=list)
    top_viewed_projects: list[ProjectViewStat] = Field(default_factory=list)
    referrers: dict[str, int] = Field(default_factory=dict)
    devices: dict[str, int] = Field(default_factory=dict)


class RecordEventRequest(BaseModel):
    event_type: str = "page_view"
    project_id: Optional[uuid.UUID] = None
    referrer: Optional[str] = None


class AIPortfolioAssistRequest(BaseModel):
    assist_type: str  # improve_summary, project_description, role_tailoring, gap_analysis
    current_text: Optional[str] = None
    target_role: Optional[str] = None
    project_title: Optional[str] = None
    tech_stack: Optional[list[str]] = None
    rough_notes: Optional[str] = None


class AIPortfolioAssistResponse(BaseModel):
    suggested_content: str
    explanation: str
    bullet_points: list[str] = Field(default_factory=list)
    is_fallback: bool = False
    grounded_evidence: list[str] = Field(default_factory=list)


class SlugUpdateRequest(BaseModel):
    public_slug: str
