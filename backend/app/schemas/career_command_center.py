from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CareerOverviewKPIs(BaseModel):
    """Consolidated KPI metrics derived from real database records."""

    total_discovered_jobs: int = Field(
        ..., description="Total public job listings ingested into the Nexora platform."
    )
    active_verified_jobs: int = Field(
        ..., description="Currently active and verified job opportunities."
    )
    strong_job_matches: int = Field(
        ..., description="Job matches with a deterministic alignment score >= 75.0."
    )
    saved_opportunities: int = Field(
        ..., description="Opportunities bookmarked by the user or marked as interested."
    )
    applications_in_progress: int = Field(
        ...,
        description="Applications in preparing, shortlisted, assessment, or interview stages.",
    )
    applications_submitted: int = Field(
        ..., description="Applications confirmed submitted or in subsequent review stages."
    )
    interviews_scheduled: int = Field(
        ...,
        description="Applications currently in interview stage or with active interview events.",
    )
    offers_received: int = Field(
        ..., description="Applications successfully resulting in a formal job offer."
    )
    resume_versions_created: int = Field(
        ..., description="Total resume versions (base and tailored) owned by the candidate."
    )
    interview_prep_sessions_completed: int = Field(
        ..., description="Interview coaching and mock evaluation sessions completed."
    )
    weekly_application_target: int = Field(
        default=5, description="Weekly application goal set by candidate."
    )
    applications_this_week: int = Field(
        default=0, description="Applications submitted during the current calendar week."
    )
    target_progress_percentage: float = Field(
        default=0.0, description="Percentage of weekly application goal achieved."
    )
    date_range: str = Field(
        default="all", description="Active date filter applied ('30d', '90d', 'all')."
    )


class FunnelStageItem(BaseModel):
    """Represents a discrete stage in the job search conversion funnel."""

    stage_id: str = Field(..., description="Unique stage identifier.")
    label: str = Field(..., description="Human-readable stage label.")
    count: int = Field(..., description="Count of opportunities/applications reaching this stage.")
    conversion_from_previous_percentage: Optional[float] = Field(
        default=None, description="Percentage converted from the immediately preceding stage."
    )
    drop_off_count: int = Field(
        default=0, description="Volume dropped off between previous stage and this stage."
    )
    drop_off_percentage: float = Field(
        default=0.0, description="Drop-off percentage from previous stage."
    )


class FunnelOutcomes(BaseModel):
    """Overall disposition and terminal status counts of user applications."""

    active: int = Field(default=0, description="Applications currently active in pipeline.")
    offered: int = Field(default=0, description="Applications culminating in an offer.")
    rejected: int = Field(default=0, description="Applications rejected by employer.")
    withdrawn: int = Field(default=0, description="Applications withdrawn by candidate.")


class CareerFunnelResponse(BaseModel):
    """7-stage visual application funnel with conversion statistics."""

    stages: list[FunnelStageItem] = Field(
        ...,
        description=(
            "Ordered funnel stages: Discovered -> Matched -> Saved -> "
            "Preparing -> Applied -> Interview -> Offer."
        ),
    )
    outcomes: FunnelOutcomes = Field(
        ..., description="Current status distribution of candidate applications."
    )
    methodology_notes: str = Field(
        default=(
            "Funnel counts are derived strictly from persisted application status transitions. "
            "Opening an external application portal is never treated as a submission."
        )
    )


class DemonstratedSkillItem(BaseModel):
    """Skill backed by concrete evidence from candidate's resume or projects."""

    skill: str
    evidence_count: int
    source_sections: list[str] = Field(default_factory=list)
    category: Optional[str] = None


class RequestedSkillItem(BaseModel):
    """Frequently requested skill across active target-role job postings."""

    skill: str
    frequency: int
    is_demonstrated_by_user: bool = False


class SkillGapItem(BaseModel):
    """Skill frequently demanded by target jobs but missing or unevidenced on resume."""

    skill: str
    market_demand_frequency: int
    status: Literal["missing_entirely", "unevidenced_mention"]
    recommendation: str


class ProjectEvidenceItem(BaseModel):
    """Quantified project or employment accomplishment from candidate history."""

    title: str
    role_or_context: str
    measurable_outcomes: list[str] = Field(default_factory=list)
    demonstrated_technologies: list[str] = Field(default_factory=list)


class InterviewPrepOverview(BaseModel):
    """Aggregated mock interview coaching and rubric performance data."""

    completed_sessions_count: int = 0
    evaluated_answers_count: int = 0
    average_overall_score: Optional[float] = None
    rubric_averages: dict[str, float] = Field(default_factory=dict)
    top_strengths: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)


class TargetRoleAlignment(BaseModel):
    """Deterministic role-family fit indicators."""

    target_role_families: list[str] = Field(default_factory=list)
    average_match_score: float = 0.0
    alignment_tier: str = "Developing"  # High, Moderate, Developing


class CareerReadinessResponse(BaseModel):
    """Personalized career readiness overview with deterministic scoring."""

    readiness_score: float = Field(
        ..., ge=0.0, le=100.0, description="Deterministic overall career readiness score (0-100)."
    )
    readiness_score_formula: str = Field(
        ..., description="Exact mathematical formula and weight breakdown used."
    )
    score_limitations: str = Field(
        ..., description="Clear disclosure of score limitations and evidence dependencies."
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Component sub-scores (0-100 each)."
    )
    demonstrated_skills: list[DemonstratedSkillItem] = Field(default_factory=list)
    frequently_requested_skills: list[RequestedSkillItem] = Field(default_factory=list)
    missing_or_underrepresented_skills: list[SkillGapItem] = Field(default_factory=list)
    project_and_internship_evidence: list[ProjectEvidenceItem] = Field(default_factory=list)
    interview_performance: InterviewPrepOverview = Field(default_factory=InterviewPrepOverview)
    target_role_alignment: TargetRoleAlignment = Field(default_factory=TargetRoleAlignment)


class NextActionItem(BaseModel):
    """Prioritized, actionable career recommendation with direct navigation."""

    id: str
    priority: Literal["high", "medium", "low"]
    action_type: Literal[
        "prepare_interview",
        "research_company",
        "complete_prep",
        "follow_up",
        "tailor_resume",
        "review_match",
        "skill_gap",
    ]
    title: str
    reason: str
    related_entity_type: Optional[str] = None  # job, application, company, skill, prep_session
    related_entity_id: Optional[str] = None
    navigation_url: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationsResponse(BaseModel):
    """List of prioritized next steps."""

    actions: list[NextActionItem] = Field(default_factory=list)
    total_actions: int = 0


class ActivityDataPoint(BaseModel):
    """Time-series data point for application volume."""

    period: str  # YYYY-MM-DD or YYYY-MM
    applications_created: int = 0
    applications_submitted: int = 0
    interviews_scheduled: int = 0


class CategoryCount(BaseModel):
    """Frequency count for a categorized metric."""

    category: str
    count: int
    percentage: float = 0.0


class StatusCount(BaseModel):
    """Frequency count for an application status."""

    status: str
    count: int
    percentage: float = 0.0


class SkillFrequencyItem(BaseModel):
    """Skill match frequency."""

    skill: str
    count: int


class LocationCount(BaseModel):
    """Job location distribution."""

    location: str
    count: int


class SavedVsAppliedComparison(BaseModel):
    """Comparison of saved opportunities vs submitted applications."""

    saved_count: int = 0
    applied_count: int = 0
    ratio: float = 0.0
    insight: str


class PerformanceAnalyticsResponse(BaseModel):
    """Unified job search performance analytics with statistical safeguards."""

    date_range: str = "all"
    weekly_activity: list[ActivityDataPoint] = Field(default_factory=list)
    monthly_activity: list[ActivityDataPoint] = Field(default_factory=list)
    applications_by_role_family: list[CategoryCount] = Field(default_factory=list)
    applications_by_company_category: list[CategoryCount] = Field(default_factory=list)
    interview_conversion_rate: Optional[float] = None
    interview_sample_size: int = 0
    is_interview_sample_meaningful: bool = False
    offer_conversion_rate: Optional[float] = None
    offer_sample_size: int = 0
    is_offer_sample_meaningful: bool = False
    application_status_distribution: list[StatusCount] = Field(default_factory=list)
    most_frequently_matched_skills: list[SkillFrequencyItem] = Field(default_factory=list)
    most_common_job_locations: list[LocationCount] = Field(default_factory=list)
    saved_vs_applied: SavedVsAppliedComparison


class CareerGoalsResponse(BaseModel):
    """Unified career goals and preferences integrated with UserMatchingPreference."""

    target_role_families: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    work_arrangement_preferences: list[str] = Field(default_factory=list)
    min_salary: Optional[float] = None
    salary_currency: Optional[str] = "INR"
    salary_period: Optional[str] = "annual"
    preferred_company_categories: list[str] = Field(default_factory=list)
    priority_technical_skills: list[str] = Field(default_factory=list)
    weekly_application_target: int = 5


class CareerGoalsUpdate(BaseModel):
    """Payload to update career goals and preferences."""

    target_role_families: Optional[list[str]] = None
    preferred_locations: Optional[list[str]] = None
    work_arrangement_preferences: Optional[list[str]] = None
    min_salary: Optional[float] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    preferred_company_categories: Optional[list[str]] = None
    priority_technical_skills: Optional[list[str]] = None
    weekly_application_target: Optional[int] = Field(default=None, ge=1, le=100)
