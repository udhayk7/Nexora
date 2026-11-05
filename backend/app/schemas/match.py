import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobResponse


class UserMatchingPreferenceBase(BaseModel):
    """Core matching preference attributes specified by user."""

    target_role_families: list[str] = Field(
        default_factory=list,
        description="Target role families (e.g. 'backend_engineer', 'frontend_engineer')",
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description="Preferred cities, countries, or regions (e.g. 'Bengaluru', 'India', 'Remote')",
    )
    work_arrangement_preferences: list[str] = Field(
        default_factory=list,
        description="Arrangements accepted (e.g. 'remote', 'hybrid', 'onsite')",
    )
    min_salary: Optional[float] = Field(
        default=None,
        ge=0,
        description="Optional minimum desired salary. Salary is never filtered if None.",
    )
    salary_currency: Optional[str] = Field(
        default="INR",
        max_length=10,
        description="Currency code for min_salary (e.g. 'INR', 'USD')",
    )
    salary_period: Optional[str] = Field(
        default="annual",
        max_length=20,
        description="Payment period: 'annual', 'monthly', 'hourly'",
    )
    seniority_preferences: list[str] = Field(
        default_factory=list,
        description="Seniority tiers accepted (e.g. 'entry_level', 'internship', 'mid_level')",
    )
    preferred_industries: list[str] = Field(
        default_factory=list,
        description="Preferred industries or company domains",
    )
    excluded_industries: list[str] = Field(
        default_factory=list,
        description="Industries or company sectors user wishes to avoid",
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Specific technologies/skills prioritized by candidate",
    )
    excluded_terms: list[str] = Field(
        default_factory=list,
        description="Specific terms/technologies to exclude from matching results",
    )
    excluded_roles: list[str] = Field(
        default_factory=list,
        description="Job titles or roles to penalize or exclude",
    )
    preferred_company_sizes: list[str] = Field(
        default_factory=list,
        description="Preferred company scale bands (e.g. 'startup', 'scaleup', 'enterprise')",
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional unstructured preference tags",
    )


class UserMatchingPreferenceUpdate(UserMatchingPreferenceBase):
    """Payload to update matching preferences."""

    pass


class UserMatchingPreferenceResponse(UserMatchingPreferenceBase):
    """Response representation of user matching preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SignalEvidenceRef(BaseModel):
    """Resume evidence citation supporting a positive match signal."""

    section: str = Field(..., description="Resume section, e.g. 'Experience', 'Projects', 'Skills'")
    excerpt: str = Field(..., description="Grounded quote or phrase from the parsed resume")


class PositiveSignal(BaseModel):
    """Concrete match strength grounded in resume data or user preferences."""

    dimension: str = Field(
        ...,
        description="Dimension: 'skills', 'role_family', 'experience', 'location', 'compensation'",
    )
    title: str = Field(..., description="Short positive signal headline")
    description: str = Field(..., description="Detailed explanation of the alignment")
    evidence: Optional[SignalEvidenceRef] = Field(
        default=None,
        description="Specific resume excerpt backing this signal",
    )


class GapSignal(BaseModel):
    """Missing requirement or true mismatch identified between resume and job."""

    type: Literal["missing", "mismatch"] = Field(
        ...,
        description="'missing' means info not found; 'mismatch' means contradictory criteria",
    )
    dimension: str = Field(
        ...,
        description="Dimension: 'skills', 'role_family', 'experience', 'location', 'compensation'",
    )
    title: str = Field(..., description="Short gap headline")
    description: str = Field(..., description="Detailed explanation of the gap or mismatch")


SalaryStatusType = Literal[
    "matched",
    "below_minimum",
    "above_minimum",
    "undisclosed",
    "no_preference",
]


class ScoreBreakdown(BaseModel):
    """Dimension-level breakdown explaining the holistic matching score."""

    skills_score: float = Field(..., ge=0, le=100)
    role_score: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    location_score: float = Field(..., ge=0, le=100)
    salary_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Score if salary was explicit; None if undisclosed",
    )
    salary_status: SalaryStatusType
    trust_adjustment: float = Field(
        default=0.0,
        description="Score adjustment reflecting listing freshness and verification status",
    )
    trust_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Verification state and freshness tier details",
    )
    weights_applied: dict[str, float] = Field(
        default_factory=dict,
        description="Normalized dimension weights used for this calculation",
    )
    raw_weighted_score: float = Field(..., ge=0, le=100)
    final_score: float = Field(..., ge=0, le=100)
    disclaimer: str = Field(
        default=(
            "Match scores represent deterministic alignment between your parsed resume and "
            "job listing criteria. They do not predict hiring outcomes or guarantee interviews."
        )
    )


class JobMatchRunRequest(BaseModel):
    """Request payload to trigger matching for a resume version."""

    resume_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Specific resume ID. Defaults to latest analyzed resume if omitted.",
    )
    version_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Specific resume version ID. Defaults to current version if omitted.",
    )
    limit: Optional[int] = Field(
        default=100,
        ge=1,
        le=300,
        description="Maximum job opportunities to match and rank.",
    )
    min_score_threshold: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Optional minimum score threshold to persist.",
    )


class JobMatchStateUpdate(BaseModel):
    """Payload to save or dismiss a match."""

    is_saved: Optional[bool] = None
    is_dismissed: Optional[bool] = None


class JobMatchResponse(BaseModel):
    """Match result representing alignment between a candidate resume and a job listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    version_id: uuid.UUID
    analysis_id: uuid.UUID
    engine_version: str
    match_score: float
    score_breakdown: ScoreBreakdown
    positive_signals: list[PositiveSignal]
    gap_signals: list[GapSignal]
    is_saved: bool
    is_dismissed: bool
    created_at: datetime
    updated_at: datetime
    job: Optional[JobResponse] = None


class JobMatchListResponse(BaseModel):
    """Paginated ranked matches response."""

    items: list[JobMatchResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class JobMatchRunResult(BaseModel):
    """Summary of a matching engine execution run."""

    matches_computed: int
    matches_saved: int
    resume_id: uuid.UUID
    version_id: uuid.UUID
    analysis_id: uuid.UUID
    engine_version: str
    message: str
