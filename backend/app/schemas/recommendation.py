import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobIntelligenceResponse(BaseModel):
    """Structured evidence-grounded intelligence for a job requisition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    content_hash: str
    provider: str
    model: str
    status: str
    error_message: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: dict[str, Any] = Field(default_factory=dict)
    educational_qualifications: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tools_and_frameworks: list[str] = Field(default_factory=list)
    seniority_level: str
    work_arrangement: str
    compensation_info: Optional[dict[str, Any]] = None
    application_requirements: list[str] = Field(default_factory=list)
    evidence_excerpts: dict[str, Any] = Field(default_factory=dict)
    is_deterministic_fallback: bool
    created_at: datetime
    updated_at: datetime


class AIJobMatchResponse(BaseModel):
    """Personalized AI-assisted assessment between a resume version and a job requisition."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID
    job_intelligence_id: Optional[uuid.UUID] = None
    assessment_hash: str
    compatibility_rating: str
    fit_score: Optional[float] = None
    fit_summary: str
    strengths: list[dict[str, Any]] = Field(default_factory=list)
    skill_gaps: list[dict[str, Any]] = Field(default_factory=list)
    experience_alignment: dict[str, Any] = Field(default_factory=dict)
    transferable_skills: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    recommendation_rationale: str
    next_steps: list[dict[str, Any]] = Field(default_factory=list)
    evidence_citations: list[dict[str, Any]] = Field(default_factory=list)
    provider: str
    model: str
    status: str
    error_message: Optional[str] = None
    is_deterministic_fallback: bool
    created_at: datetime


class RecommendationExplanation(BaseModel):
    """Grounded explanation of why a job matches and potential gaps."""

    why_matches: dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant skills, experience, projects, and preference alignment",
    )
    potential_gaps: dict[str, Any] = Field(
        default_factory=dict,
        description="Missing skills, experience gaps, qualification mismatches",
    )
    recommended_next_steps: list[str] = Field(
        default_factory=list,
        description="Actionable next steps (tailor resume, review details, track app)",
    )


class JobRecommendationItem(BaseModel):
    """A personalized job recommendation with match metrics and grounded explanations."""

    job_id: uuid.UUID
    title: str
    company_name: str
    company_logo_url: Optional[str] = None
    location_text: Optional[str] = None
    work_arrangement: str
    role_family: Optional[str] = None
    seniority_level: Optional[str] = None
    employment_type: Optional[str] = None
    job_url: str
    application_url: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    salary_disclosed: bool = False
    verification_status: str
    freshness: str
    deterministic_score: float
    recommendation_score: float
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    is_saved: bool = False
    is_dismissed: bool = False
    has_applied: bool = False
    ai_evaluated: bool = False
    ai_compatibility_rating: Optional[str] = None
    ai_fit_score: Optional[float] = None
    explanation: RecommendationExplanation
    first_seen_at: datetime


class RecommendationListResponse(BaseModel):
    """Paginated list of personalized recommendations."""

    items: list[JobRecommendationItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    active_resume_version_id: Optional[uuid.UUID] = None
    active_resume_title: Optional[str] = None
    stats: dict[str, Any] = Field(default_factory=dict)


class RecommendationRefreshRequest(BaseModel):
    """Payload to trigger recommendations refresh and optional top-N AI evaluation."""

    resume_version_id: Optional[uuid.UUID] = None
    evaluate_top_ai: bool = False
    max_ai_evaluations: int = Field(default=3, ge=1, le=10)


class RecommendationRefreshResponse(BaseModel):
    """Response returned upon refreshing recommendations."""

    message: str
    recommendations_count: int
    ai_evaluations_run: int


class RecommendationStateUpdateRequest(BaseModel):
    """Payload to save or dismiss a job recommendation."""

    is_saved: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class RecommendationStateResponse(BaseModel):
    """Response for job recommendation state update."""

    job_id: uuid.UUID
    is_saved: bool
    is_dismissed: bool

