import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    section: str = Field(..., description="Source resume section name, e.g. Experience, Education")
    excerpt: str = Field(..., description="Short quote or evidence excerpt from resume text")


class CandidateProfile(BaseModel):
    summary: str = Field(
        ..., description="Concise candidate profile summary based strictly on resume"
    )
    domains: list[str] = Field(
        default_factory=list, description="Primary technical/professional domains"
    )
    career_level_estimate: str = Field(
        ...,
        description="Estimated career level (e.g. Senior, Mid-Level) clearly labeled as estimate",
    )
    evidence: list[EvidenceItem] = Field(default_factory=list)


class SkillsAnalysis(BaseModel):
    categorized_skills: dict[str, list[str]] = Field(
        default_factory=dict, description="Extracted skills grouped into categories"
    )
    supported_skills: list[str] = Field(
        default_factory=list, description="Skills supported by project or employment evidence"
    )
    unevidenced_skills: list[str] = Field(
        default_factory=list,
        description="Skills mentioned but lacking supporting context in experience",
    )
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ExperienceEvidence(BaseModel):
    summary: str = Field(..., description="Summary of work and project history")
    measurable_outcomes: list[str] = Field(
        default_factory=list, description="Quantified achievements and metrics explicitly stated"
    )
    vague_or_unsupported_claims: list[str] = Field(
        default_factory=list, description="Claims that lack metrics, specificity, or context"
    )
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ResumeStrength(BaseModel):
    strength: str = Field(..., description="Identified strength grounded in evidence")
    evidence: EvidenceItem


class ImprovementOpportunity(BaseModel):
    category: str = Field(
        ...,
        description="Category: missing_info, vague_bullet, repetition, formatting",
    )
    issue: str = Field(..., description="Specific weakness or clarity concern observed")
    suggestion: str = Field(..., description="Actionable suggestion to clarify existing evidence")
    referenced_excerpt: Optional[str] = None


class RoleSuitability(BaseModel):
    role_name: str = Field(
        ...,
        description="Role family (e.g. AI / Machine Learning Engineer, Python Backend Developer)",
    )
    suitability_band: str = Field(
        ..., description="Band: Strong Match, Good Match, Moderate Match, Developing Match"
    )
    heuristic_score: int = Field(
        ..., ge=0, le=100, description="Heuristic score (0-100) based strictly on evidenced skills"
    )
    confidence: str = Field(..., description="Confidence level: High, Medium, Low")
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Heuristic AI assessment based on resume evidence, not a hiring guarantee."
    )


class ActionableRecommendation(BaseModel):
    priority: str = Field(..., description="high, medium, or low priority")
    title: str = Field(..., description="Short recommendation title")
    issue: str = Field(..., description="What to improve")
    why_it_matters: str = Field(
        ..., description="Why this change strengthens candidate presentation"
    )
    suggested_action: str = Field(
        ..., description="Action user can take using their authentic experience"
    )
    referenced_evidence: Optional[str] = None


class ResumeAnalysisResult(BaseModel):
    profile: CandidateProfile
    skills: SkillsAnalysis
    experience_evidence: ExperienceEvidence
    strengths: list[ResumeStrength] = Field(default_factory=list)
    improvement_opportunities: list[ImprovementOpportunity] = Field(default_factory=list)
    role_suitability: list[RoleSuitability] = Field(default_factory=list)
    recommendations: list[ActionableRecommendation] = Field(default_factory=list)


# API Request & Response schemas
class AnalyzeResumeRequest(BaseModel):
    force_refresh: bool = Field(
        default=False, description="Whether to bypass cache and force a new AI analysis run"
    )


class ResumeAnalysisSummary(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    version_id: uuid.UUID
    status: str
    provider: str
    model: str
    career_level: Optional[str] = None
    top_domains: list[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResumeAnalysisDetail(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    version_id: uuid.UUID
    status: str
    provider: str
    model: str
    result: Optional[ResumeAnalysisResult] = None
    error_summary: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResumeAnalysisStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_summary: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
