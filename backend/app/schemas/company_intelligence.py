"""Pydantic schemas for Company Intelligence & Research module."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TechnologyItemSchema(BaseModel):
    """Specific technology identified with provenance and evidence strength."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Canonical name of the technology/tool/language")
    category: str = Field(
        ...,
        description="languages, frameworks, cloud_platforms, databases, aiml, devops, tools, other",
    )
    evidence_strength: str = Field(
        ...,
        description=(
            "confirmed (official mention), supported (job postings), inferred (ecosystem), unknown"
        ),
    )
    evidence_source: str = Field(
        ...,
        description="Citation or source description proving this technology",
    )
    context: Optional[str] = Field(
        None,
        description="Contextual snippet of how the technology is utilized",
    )


class CompanyProductOrService(BaseModel):
    """Product, service, or offering with evidence."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str
    category: Optional[str] = None
    evidence_source: Optional[str] = None


class RecentDevelopmentItem(BaseModel):
    """Recent news, product release, or announcement."""

    model_config = ConfigDict(from_attributes=True)

    headline: str
    summary: str
    source_url: Optional[str] = None
    date: Optional[str] = None


class HiringSummarySchema(BaseModel):
    """Aggregated hiring metrics computed from verified job records in Nexora DB."""

    model_config = ConfigDict(from_attributes=True)

    total_active_jobs: int = 0
    entry_level_jobs: int = 0
    internship_jobs: int = 0
    experienced_jobs: int = 0
    top_categories: list[dict[str, Any]] = Field(default_factory=list)
    top_locations: list[str] = Field(default_factory=list)
    active_technologies: list[str] = Field(default_factory=list)
    stale_or_expired_jobs: int = 0
    last_job_posted_at: Optional[str] = None


class CompanyIntelligenceResponse(BaseModel):
    """Comprehensive company intelligence profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    overview: Optional[str] = None
    industry_domain: Optional[str] = None
    headquarters: Optional[str] = None
    operating_locations: list[str] = Field(default_factory=list)
    website_url: Optional[str] = None
    careers_url: Optional[str] = None
    products_and_services: list[CompanyProductOrService] = Field(default_factory=list)
    technology_stack: list[TechnologyItemSchema] = Field(default_factory=list)
    size_band: Optional[str] = None
    size_evidence: Optional[str] = None
    funding_ownership_info: Optional[str] = None
    recent_developments: list[RecentDevelopmentItem] = Field(default_factory=list)
    hiring_summary: HiringSummarySchema = Field(default_factory=HiringSummarySchema)
    last_researched_at: Optional[datetime] = None
    is_stale: bool = False
    provenance_sources_count: int = 0
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CompanyResearchSourceResponse(BaseModel):
    """Public research document, news, or blog citation source."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    source_type: str
    source_url: str
    title: str
    content_snippet: Optional[str] = None
    content_hash: str
    retrieved_at: datetime
    published_at: Optional[datetime] = None
    is_verified: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class CompanyFitAssessmentResponse(BaseModel):
    """Candidate-to-company fit evaluation grounded in user resume and preferences."""

    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    company_name: str
    fit_score: int = Field(..., ge=0, le=100, description="Overall match score (0-100)")
    fit_level: str = Field(..., description="strong, moderate, developing")
    matching_skills: list[str] = Field(default_factory=list)
    missing_or_gap_skills: list[str] = Field(default_factory=list)
    role_alignment_summary: str
    target_role_matches: list[dict[str, Any]] = Field(default_factory=list)
    recommended_interview_focus: list[str] = Field(default_factory=list)
    fit_evidence: list[str] = Field(default_factory=list)


class CompanyResearchReportSection(BaseModel):
    """Individual section of the 10-section structured company research report."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    title: str
    content: str
    bullet_points: list[str] = Field(default_factory=list)


class CompanyResearchReportResponse(BaseModel):
    """Structured AI company research report."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str
    user_id: uuid.UUID
    report_title: str
    sections: dict[str, Any] = Field(default_factory=dict)
    candidate_fit: Optional[dict[str, Any]] = None
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    provider: str
    model: str
    is_cached: bool = False
    is_deterministic_fallback: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class CompanyResearchGenerateRequest(BaseModel):
    """Request payload to generate or refresh a comprehensive company research report."""

    force_refresh: bool = Field(
        default=False,
        description="Bypass cached report and re-run research generation",
    )
    focus_areas: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional specific areas to emphasize "
            "(e.g. ['tech_stack', 'engineering_culture', 'entry_level'])"
        ),
    )
    resume_version_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional resume version to assess candidate-company fit against",
    )
