import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CareerWorkflowStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    step_name: str
    step_order: int
    status: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CareerWorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workflow_type: str
    status: str
    target_job_id: Optional[uuid.UUID] = None
    target_application_id: Optional[uuid.UUID] = None
    current_step: str
    progress_pct: int
    step_data: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    idempotency_key: Optional[str] = None
    requires_approval: bool
    is_approved: bool
    approved_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    steps: list[CareerWorkflowStepResponse] = Field(default_factory=list)


class OnboardingStartRequest(BaseModel):
    resume_id: Optional[uuid.UUID] = None
    preferences_override: Optional[dict[str, Any]] = None


class OnboardingConfirmRequest(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    work_arrangement_preferences: list[str] = Field(default_factory=list)
    min_salary: Optional[float] = None
    salary_currency: Optional[str] = "INR"
    seniority: Optional[str] = "entry"


class OnboardingResultResponse(BaseModel):
    workflow_run_id: uuid.UUID
    status: str
    candidate_summary: dict[str, Any] = Field(default_factory=dict)
    extracted_roles: list[str] = Field(default_factory=list)
    extracted_skills: list[str] = Field(default_factory=list)
    inferred_preferences: dict[str, Any] = Field(default_factory=dict)
    matching_jobs_count: int = 0
    top_matches: list[dict[str, Any]] = Field(default_factory=list)


class UnifiedOpportunityItem(BaseModel):
    job_id: uuid.UUID
    title: str
    company_name: str
    company_id: Optional[uuid.UUID] = None
    company_tier: Optional[str] = None
    company_type: Optional[str] = None
    location: Optional[str] = None
    work_arrangement: Optional[str] = None
    experience_level: Optional[str] = None
    is_entry_level: bool = False
    is_verified: bool = False
    verification_status: str = "unverified"
    match_score: Optional[float] = None
    match_reasons: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    eligibility_concerns: list[str] = Field(default_factory=list)
    application_url: Optional[str] = None
    source_name: Optional[str] = None
    published_at: Optional[str] = None


class UnifiedDiscoveryResponse(BaseModel):
    total_active_jobs: int
    entry_level_count: int
    priority_companies_count: int
    opportunities: list[UnifiedOpportunityItem] = Field(default_factory=list)
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class PreparationStartRequest(BaseModel):
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None


class PreparationDetailResponse(BaseModel):
    preparation_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company_name: str
    application_id: Optional[uuid.UUID] = None
    execution_status: str
    execution_channel: Optional[str] = None
    checklist_status: str
    checklist_items: list[dict[str, Any]] = Field(default_factory=list)
    job_intelligence: Optional[dict[str, Any]] = None
    compatibility_assessment: Optional[dict[str, Any]] = None
    tailored_resume: Optional[dict[str, Any]] = None
    cover_letter: Optional[dict[str, Any]] = None
    recruiter_email: Optional[dict[str, Any]] = None
    qa_prep: list[dict[str, Any]] = Field(default_factory=list)
    company_research: Optional[dict[str, Any]] = None
    interview_prep_starter: Optional[dict[str, Any]] = None
    can_apply: bool = False
    portal_url: Optional[str] = None


class ApprovePreparationRequest(BaseModel):
    channel: str = "official_portal"  # "official_portal", "gmail", "external_form"
    notes: Optional[str] = None


class PortalOpenResponse(BaseModel):
    portal_url: str
    assisted_form_data: dict[str, Any]
    execution_status: str
    opened_at: str


class PortalConfirmRequest(BaseModel):
    confirmation_notes: Optional[str] = None


class GmailExecuteRequest(BaseModel):
    email_id: uuid.UUID
    confirm_send: bool = True


class WorkflowRecommendedAction(BaseModel):
    action_type: str
    title: str
    description: str
    priority: str  # "high", "medium", "low"
    target_route: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDashboardResponse(BaseModel):
    profile_completion_pct: int
    profile_missing_items: list[str] = Field(default_factory=list)
    new_opportunities_count: int = 0
    recommended_opportunities_count: int = 0
    jobs_requiring_review_count: int = 0
    applications_awaiting_approval_count: int = 0
    applications_submitted_count: int = 0
    incomplete_preparations_count: int = 0
    upcoming_interviews_count: int = 0
    recommended_next_actions: list[WorkflowRecommendedAction] = Field(default_factory=list)
    recent_workflow_runs: list[CareerWorkflowRunResponse] = Field(default_factory=list)
