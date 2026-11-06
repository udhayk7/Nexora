import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ApplicationStatus = Literal[
    "interested",
    "preparing",
    "applied",
    "shortlisted",
    "assessment",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
]

ApplicationChannel = Literal[
    "official_portal",
    "email",
    "referral",
    "external_form",
    "other",
]

ActivityType = Literal[
    "application_submitted",
    "status_changed",
    "assessment_scheduled",
    "assessment_completed",
    "interview_scheduled",
    "interview_completed",
    "recruiter_communication",
    "follow_up_completed",
    "offer_received",
    "personal_note",
    "other",
]

InterviewType = Literal[
    "screening",
    "technical",
    "behavioral",
    "system_design",
    "take_home_assessment",
    "online_assessment",
    "final_round",
    "other",
]

InterviewStatus = Literal[
    "scheduled",
    "completed",
    "cancelled",
    "rescheduled",
]

InterviewOutcome = Literal[
    "pending",
    "passed",
    "failed",
    "inconclusive",
    "withdrawn",
]


# --- Status History ---


class ApplicationStatusHistoryResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    changed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Activities ---


class ApplicationActivityCreate(BaseModel):
    activity_type: ActivityType = "personal_note"
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    activity_date: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None


class ApplicationActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    activity_date: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None


class ApplicationActivityResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    activity_type: str
    title: str
    description: Optional[str] = None
    activity_date: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Interviews & Assessments ---


class ApplicationInterviewCreate(BaseModel):
    interview_type: InterviewType = "technical"
    title: str = Field(..., min_length=1, max_length=255)
    round_number: int = Field(default=1, ge=1)
    scheduled_at: datetime
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    meeting_url: Optional[str] = Field(None, max_length=500)
    interviewer_names: Optional[str] = Field(None, max_length=255)
    preparation_notes: Optional[str] = None
    feedback: Optional[str] = None
    status: InterviewStatus = "scheduled"
    outcome: InterviewOutcome = "pending"
    next_steps: Optional[str] = None


class ApplicationInterviewUpdate(BaseModel):
    interview_type: Optional[InterviewType] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    round_number: Optional[int] = Field(None, ge=1)
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=480)
    meeting_url: Optional[str] = Field(None, max_length=500)
    interviewer_names: Optional[str] = Field(None, max_length=255)
    preparation_notes: Optional[str] = None
    feedback: Optional[str] = None
    status: Optional[InterviewStatus] = None
    outcome: Optional[InterviewOutcome] = None
    next_steps: Optional[str] = None


class ApplicationInterviewResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    user_id: uuid.UUID
    interview_type: str
    title: str
    round_number: int
    scheduled_at: datetime
    duration_minutes: Optional[int] = None
    meeting_url: Optional[str] = None
    interviewer_names: Optional[str] = None
    preparation_notes: Optional[str] = None
    feedback: Optional[str] = None
    status: str
    outcome: str
    next_steps: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Job Application CRUD ---


class JobApplicationCreate(BaseModel):
    job_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    status: ApplicationStatus = "interested"
    application_channel: ApplicationChannel = "official_portal"
    application_url: Optional[str] = Field(None, max_length=500)
    applied_at: Optional[datetime] = None
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    recruiter_name: Optional[str] = Field(None, max_length=150)
    recruiter_email: Optional[str] = Field(None, max_length=255)
    recruiter_phone: Optional[str] = Field(None, max_length=50)
    deadline_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    submission_confirmed: bool = False
    metadata_json: Optional[dict[str, Any]] = None


class JobApplicationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    company_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    application_channel: Optional[ApplicationChannel] = None
    application_url: Optional[str] = Field(None, max_length=500)
    applied_at: Optional[datetime] = None
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    recruiter_name: Optional[str] = Field(None, max_length=150)
    recruiter_email: Optional[str] = Field(None, max_length=255)
    recruiter_phone: Optional[str] = Field(None, max_length=50)
    deadline_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    submission_confirmed: Optional[bool] = None
    metadata_json: Optional[dict[str, Any]] = None


class JobApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    submission_confirmed: Optional[bool] = None


class JobApplicationSummaryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    title: str
    company_name: str
    status: str
    application_channel: str
    applied_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    submission_confirmed: bool = False
    interviews_count: int = 0
    activities_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobApplicationDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    title: str
    company_name: str
    status: str
    application_channel: str
    application_url: Optional[str] = None
    applied_at: Optional[datetime] = None
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    resume_title: Optional[str] = None
    resume_version_number: Optional[int] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_phone: Optional[str] = None
    deadline_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    submission_confirmed: bool = False
    link_opened_at: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    interviews_count: int = 0
    activities_count: int = 0
    created_at: datetime
    updated_at: datetime
    status_history: list[ApplicationStatusHistoryResponse] = Field(default_factory=list)
    activities: list[ApplicationActivityResponse] = Field(default_factory=list)
    interviews: list[ApplicationInterviewResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class JobApplicationListResponse(BaseModel):
    items: list[JobApplicationSummaryResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# --- Analytics ---


class ApplicationAnalyticsResponse(BaseModel):
    total_applications: int
    in_progress_count: int
    interviews_scheduled_count: int
    assessments_pending_count: int
    offers_count: int
    rejections_count: int
    upcoming_deadlines_count: int
    upcoming_follow_ups_count: int
    status_distribution: dict[str, int]
    channel_distribution: dict[str, int]
    activity_trend: list[dict[str, Any]]
    upcoming_events: list[dict[str, Any]]
