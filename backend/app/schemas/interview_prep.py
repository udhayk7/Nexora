import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Session Setup & Preparation Plan
# ============================================================================


class InterviewSessionCreateRequest(BaseModel):
    """Payload to initiate a grounded interview preparation or mock session."""

    job_id: Optional[uuid.UUID] = Field(None, description="Target job opportunity requisition")
    company_id: Optional[uuid.UUID] = Field(None, description="Target hiring company")
    application_id: Optional[uuid.UUID] = Field(
        None, description="Linked application tracking record"
    )
    resume_version_id: Optional[uuid.UUID] = Field(
        None, description="Candidate resume version providing verified facts"
    )
    interview_round: str = Field(
        default="technical",
        description=(
            "screening, technical, coding, system_design, behavioral, managerial, final_round"
        ),
    )
    interview_type: str = Field(
        default="mock_interview",
        description="mock_interview, project_deep_dive, technical_revision, behavioral_prep",
    )
    difficulty: str = Field(
        default="intermediate",
        description="beginner, intermediate, advanced",
    )
    category: str = Field(
        default="technical",
        description=(
            "technical, coding_problem_solving, backend_python, frontend_fullstack, "
            "ai_ml_genai, database_sql, system_design, project_deep_dive, "
            "internship_experience, behavioral_hr"
        ),
    )
    question_count: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Number of personalized interview questions to generate",
    )
    user_instructions: Optional[str] = Field(
        None,
        max_length=1500,
        description="Custom candidate focus areas, upcoming round context, or tone preference",
    )
    selected_project_name: Optional[str] = Field(
        None,
        description="Specific project from verified resume for deep-dive coaching",
    )


class PreparationPlanTopic(BaseModel):
    topic: str
    rationale: str
    suggested_focus: list[str] = Field(default_factory=list)


class PreparationPlanProject(BaseModel):
    project_name: str
    relevance_to_role: str
    talking_points: list[str] = Field(default_factory=list)
    technologies_evidenced: list[str] = Field(default_factory=list)


class PreparationPlanGap(BaseModel):
    skill_or_requirement: str
    status: str  # missing_direct_evidence, adjacent_transferable
    mitigation_strategy: str


class PreparationPlanBehavioral(BaseModel):
    competency: str
    prompt_theme: str
    relevant_experience_anchor: str


class InterviewPreparationPlan(BaseModel):
    """Grounded interview preparation plan."""

    technical_topics_to_revise: list[PreparationPlanTopic] = Field(default_factory=list)
    relevant_projects_to_explain: list[PreparationPlanProject] = Field(default_factory=list)
    internship_and_experience_talking_points: list[str] = Field(default_factory=list)
    required_technical_skills: list[str] = Field(default_factory=list)
    potential_skill_gaps: list[PreparationPlanGap] = Field(default_factory=list)
    behavioral_preparation_topics: list[PreparationPlanBehavioral] = Field(default_factory=list)
    company_and_role_context: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Question, Answer, and Evaluation Schemas
# ============================================================================


class InterviewEvaluationDetail(BaseModel):
    """Multi-dimensional rubric evaluation of candidate's answer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    answer_id: uuid.UUID
    session_id: uuid.UUID
    overall_score: float
    technical_correctness_score: float
    relevance_score: float
    completeness_score: float
    clarity_score: float
    approach_score: float
    communication_score: float
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(default_factory=list)
    stronger_answer_example: str
    evaluation_feedback: str
    provider: Optional[str] = None
    model: Optional[str] = None
    is_deterministic_fallback: bool = False
    created_at: datetime


class InterviewAnswerDetail(BaseModel):
    """Submitted candidate answer and associated evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    question_id: uuid.UUID
    user_id: uuid.UUID
    answer_text: str
    submitted_code: Optional[str] = None
    submitted_language: Optional[str] = None
    time_spent_seconds: Optional[int] = None
    created_at: datetime
    evaluation: Optional[InterviewEvaluationDetail] = None


class InterviewAnswerSubmitRequest(BaseModel):
    """Payload when submitting an answer to an interview question."""

    answer_text: str = Field(
        ...,
        min_length=5,
        max_length=15000,
        description="Candidate's spoken or written answer",
    )
    submitted_code: Optional[str] = Field(
        None,
        max_length=20000,
        description="Optional code solution (evaluated statically)",
    )
    submitted_language: Optional[str] = Field(
        None,
        max_length=50,
        description="Programming language (e.g. python, typescript, sql)",
    )
    time_spent_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Time spent answering in seconds",
    )


class InterviewQuestionDetail(BaseModel):
    """Individual question with rubrics and candidate's answer if submitted."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    question_order: int
    category: str
    difficulty: str
    question_text: str
    context_hint: Optional[str] = None
    expected_points: list[str] = Field(default_factory=list)
    evaluation_criteria: dict[str, Any] = Field(default_factory=dict)
    ideal_answer_outline: Optional[str] = None
    project_name: Optional[str] = None
    created_at: datetime
    answers: list[InterviewAnswerDetail] = Field(default_factory=list)


# ============================================================================
# Session Summaries & Details
# ============================================================================


class InterviewSessionSummary(BaseModel):
    """Summary representation for session lists."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    title: str
    interview_type: str
    interview_round: str
    difficulty: str
    category: str
    status: str
    total_questions: int
    completed_questions: int
    average_score: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Contextual display fields
    job_title: Optional[str] = None
    company_name: Optional[str] = None


class InterviewSessionDetail(InterviewSessionSummary):
    """Full preparation session with questions, answers, and evaluations."""

    preparation_plan: dict[str, Any] = Field(default_factory=dict)
    user_instructions: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    is_deterministic_fallback: bool = False
    questions: list[InterviewQuestionDetail] = Field(default_factory=list)


# ============================================================================
# Project Deep-Dive Coaching
# ============================================================================


class ProjectPreparationGenerateRequest(BaseModel):
    """Request structured project interview preparation for an evidenced project."""

    project_name: str = Field(..., description="Project name from verified resume")
    job_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    user_instructions: Optional[str] = None


class StructuredProjectBreakdown(BaseModel):
    """Grounded project interview blueprint."""

    project_name: str
    overview_pitch: str
    architecture_and_design: str
    technical_implementation: list[str] = Field(default_factory=list)
    key_challenges_and_solutions: list[dict[str, str]] = Field(default_factory=list)
    scalability_and_improvements: list[str] = Field(default_factory=list)
    candidate_contribution: str
    practice_questions: list[str] = Field(default_factory=list)


# ============================================================================
# Preparation Notes & Checklists
# ============================================================================


class InterviewNoteCreateRequest(BaseModel):
    """Save an interview note, revision topic, company research, or checklist."""

    session_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    note_type: str = Field(
        default="general",
        description="topics_to_revise, questions_to_ask, company_research, checklist, general",
    )
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(default="")
    items: list[dict[str, Any]] = Field(default_factory=list)
    is_pinned: bool = False


class InterviewNoteUpdateRequest(BaseModel):
    """Update an existing interview preparation note."""

    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    items: Optional[list[dict[str, Any]]] = None
    is_pinned: Optional[bool] = None


class InterviewNoteResponse(BaseModel):
    """Stored interview preparation note."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    note_type: str
    title: str
    content: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Performance Analytics
# ============================================================================


class ScoreTrendPoint(BaseModel):
    session_id: uuid.UUID
    date: datetime
    score: float
    title: str
    category: str


class InterviewAnalyticsResponse(BaseModel):
    """Comprehensive performance dashboard metrics based only on real completed sessions."""

    total_sessions_started: int
    total_sessions_completed: int
    total_questions_attempted: int
    overall_average_score: float
    technical_average_score: float
    behavioral_average_score: float
    category_performance: dict[str, float] = Field(default_factory=dict)
    difficulty_performance: dict[str, float] = Field(default_factory=dict)
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    recommended_revision_topics: list[str] = Field(default_factory=list)
    score_trend: list[ScoreTrendPoint] = Field(default_factory=list)


# ============================================================================
# Interview Reminder
# ============================================================================


class InterviewReminderCreateRequest(BaseModel):
    """Schedule an interview notification reminder."""

    application_interview_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None
    remind_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    reminder_type: Optional[str] = "interview_reminder"
    reminder_title: Optional[str] = None
    notes: Optional[str] = None
    custom_message: Optional[str] = None
