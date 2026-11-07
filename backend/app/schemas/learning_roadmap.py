import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Skill Gap Analysis Schemas
# ---------------------------------------------------------------------------


class SkillItem(BaseModel):
    skill: str
    status: str = Field(
        ...,
        description="demonstrated, partially_demonstrated, missing, or interview_weakness",
    )
    priority: str = Field(..., description="critical, high, medium, or low")
    priority_score: float = Field(..., ge=0.0, le=100.0)
    job_frequency: int = Field(default=0, ge=0)
    is_target_role_skill: bool = False
    is_priority_goal: bool = False
    interview_weakness_count: int = Field(default=0, ge=0)
    evidence_summary: Optional[str] = None
    supporting_sources: list[str] = Field(default_factory=list)


class SkillGapAnalysisResponse(BaseModel):
    demonstrated_skills: list[SkillItem] = Field(default_factory=list)
    partially_demonstrated_skills: list[SkillItem] = Field(default_factory=list)
    missing_skills: list[SkillItem] = Field(default_factory=list)
    interview_weakness_skills: list[SkillItem] = Field(default_factory=list)
    top_recommended_skills: list[SkillItem] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    total_identified_gaps: int = 0
    analysis_disclaimer: str = (
        "Skill classifications are strictly derived from verified resume evidence, "
        "discovered job requirements, and interview rubric evaluations. "
        "No skills are asserted without concrete candidate or market backing."
    )


# ---------------------------------------------------------------------------
# Learning Resource Schemas
# ---------------------------------------------------------------------------


class LearningResourceCreate(BaseModel):
    skill: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., min_length=1, max_length=1024)
    cost_tier: str = Field(default="free", pattern="^(free|paid|freemium)$")
    resource_type: str = Field(
        default="documentation",
        pattern="^(documentation|interactive_course|video_series|tutorial|book|project_guide)$",
    )
    difficulty: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    estimated_hours: float = Field(default=1.0, ge=0.0)
    description: Optional[str] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v_clean = v.strip()
        if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
            raise ValueError("Resource URL must start with http:// or https://")
        return v_clean


class LearningResourceResponse(BaseModel):
    id: uuid.UUID
    skill: str
    title: str
    provider: str
    url: str
    cost_tier: str
    resource_type: str
    difficulty: str
    estimated_hours: float
    description: Optional[str] = None
    is_curated: bool
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Roadmap Milestone Schemas
# ---------------------------------------------------------------------------


class PracticalExercise(BaseModel):
    title: str
    instructions: str
    estimated_minutes: int = 30
    completed: bool = False


class LearningMilestoneResponse(BaseModel):
    id: uuid.UUID
    roadmap_id: uuid.UUID
    title: str
    stage: str
    description: str
    learning_objectives: list[str] = Field(default_factory=list)
    practical_exercises: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    estimated_hours: float
    completed_hours: float
    order_index: int
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningMilestoneUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(not_started|in_progress|completed|skipped)$")
    completed_hours: Optional[float] = Field(None, ge=0.0)
    completion_notes: Optional[str] = None
    practical_exercises: Optional[list[dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Learning Roadmap Schemas
# ---------------------------------------------------------------------------


class RoadmapGenerateRequest(BaseModel):
    target_role: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description=(
            "Target track, e.g. 'backend_python', 'fullstack', "
            "'ai_ml', 'genai', 'data_analyst', 'sde'"
        ),
    )
    custom_skills: Optional[list[str]] = Field(
        default=None,
        description="Specific technical skills to include in the learning plan",
    )
    target_difficulty: Optional[str] = Field(
        default="intermediate",
        pattern="^(beginner|intermediate|advanced|custom)$",
    )
    user_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional instructions or career priorities",
    )


class LearningRoadmapResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    target_role: str
    description: str
    target_skills: list[str]
    status: str
    difficulty_level: str
    total_estimated_hours: float
    completed_hours: float
    completion_percentage: float
    prerequisites: list[dict[str, Any]] = Field(default_factory=list)
    already_mastered_skills: list[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    milestones: list[LearningMilestoneResponse] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningRoadmapSummary(BaseModel):
    id: uuid.UUID
    title: str
    target_role: str
    target_skills: list[str]
    status: str
    difficulty_level: str
    total_estimated_hours: float
    completed_hours: float
    completion_percentage: float
    milestones_count: int = 0
    completed_milestones_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningRoadmapStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|paused|completed|archived)$")


# ---------------------------------------------------------------------------
# Learning Project Schemas
# ---------------------------------------------------------------------------


class SuggestedMilestone(BaseModel):
    milestone_title: str
    description: str
    is_done: bool = False


class ProjectRecommendationResponse(BaseModel):
    title: str
    objective: str
    tech_stack: list[str]
    target_skills: list[str]
    functional_requirements: list[str]
    suggested_milestones: list[SuggestedMilestone]
    expected_portfolio_outcome: str
    difficulty: str
    estimated_hours: float


class LearningProjectCreate(BaseModel):
    roadmap_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=2, max_length=255)
    objective: str = Field(..., min_length=10)
    tech_stack: list[str] = Field(default_factory=list)
    target_skills: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    suggested_milestones: list[SuggestedMilestone] = Field(default_factory=list)
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    architecture_summary: Optional[str] = None
    evidence_notes: Optional[str] = None
    status: str = Field(default="planned", pattern="^(planned|in_progress|completed|abandoned)$")


class LearningProjectUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(planned|in_progress|completed|abandoned)$")
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    architecture_summary: Optional[str] = None
    evidence_notes: Optional[str] = None
    portfolio_ready: Optional[bool] = None
    suggested_milestones: Optional[list[SuggestedMilestone]] = None


class LearningProjectResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    roadmap_id: Optional[uuid.UUID] = None
    title: str
    objective: str
    tech_stack: list[str]
    target_skills: list[str]
    functional_requirements: list[str]
    suggested_milestones: list[dict[str, Any]]
    status: str
    repository_url: Optional[str] = None
    live_demo_url: Optional[str] = None
    architecture_summary: Optional[str] = None
    evidence_notes: Optional[str] = None
    portfolio_ready: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Learning Activity Schemas
# ---------------------------------------------------------------------------


class LearningActivityCreate(BaseModel):
    roadmap_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    skill: str = Field(..., min_length=1, max_length=128)
    activity_type: str = Field(
        default="practice",
        pattern="^(reading|coding|exercise|project_work|review|practice)$",
    )
    hours_spent: float = Field(..., gt=0.0, le=24.0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class LearningActivityResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    roadmap_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    skill: str
    activity_type: str
    hours_spent: float
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Learning Analytics Schemas
# ---------------------------------------------------------------------------


class LearningAnalyticsResponse(BaseModel):
    total_learning_hours: float = 0.0
    active_roadmaps_count: int = 0
    completed_roadmaps_count: int = 0
    completed_milestones_count: int = 0
    in_progress_skills_count: int = 0
    completed_projects_count: int = 0
    portfolio_ready_projects_count: int = 0
    weekly_hours_spent: float = 0.0
    hours_by_skill: dict[str, float] = Field(default_factory=dict)
    readiness_contribution_summary: str = (
        "Practice hours and completed projects build practical competency. "
        "Completed projects with verified repository links can be explicitly added "
        "to your resume in Resume Studio."
    )
