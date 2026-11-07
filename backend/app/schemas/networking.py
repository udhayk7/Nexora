import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Recruiter Profile Schemas
# ---------------------------------------------------------------------------


class RecruiterProfileBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    designation: str = Field(default="Recruiter", max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    recruitment_specialization: Optional[str] = Field(default=None, max_length=255)
    relevant_departments: list[str] = Field(default_factory=list)
    public_profile_url: Optional[str] = Field(default=None, max_length=500)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    associated_job_ids: list[str] = Field(default_factory=list)
    source_type: str = Field(
        default="manual_user_addition",
        description=(
            "official_careers_page, team_page, public_announcement, "
            "manual_user_addition, job_listing"
        ),
    )
    verification_status: str = Field(
        default="unverified",
        description="verified, inferred, unverified",
    )
    verification_notes: Optional[str] = None
    is_global: bool = True


class RecruiterCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    designation: str = Field(default="Technical Recruiter", max_length=255)
    company_id: Optional[uuid.UUID] = None
    company_name: str = Field(..., min_length=1, max_length=255)
    recruitment_specialization: Optional[str] = None
    relevant_departments: list[str] = Field(default_factory=list)
    public_profile_url: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    associated_job_ids: list[str] = Field(default_factory=list)
    source_type: str = Field(default="manual_user_addition")
    verification_notes: Optional[str] = None

    @field_validator("contact_email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                return None
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Invalid email format for recruiter contact")
        return v


class RecruiterUpdateRequest(BaseModel):
    designation: Optional[str] = None
    recruitment_specialization: Optional[str] = None
    relevant_departments: Optional[list[str]] = None
    public_profile_url: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    associated_job_ids: Optional[list[str]] = None
    verification_status: Optional[str] = None
    verification_notes: Optional[str] = None


class RecruiterProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    designation: str
    company_id: Optional[uuid.UUID] = None
    company_name: str
    recruitment_specialization: Optional[str] = None
    relevant_departments: list[str] = Field(default_factory=list)
    public_profile_url: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    associated_job_ids: list[str] = Field(default_factory=list)
    source_type: str
    verification_status: str
    verification_notes: Optional[str] = None
    is_global: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Recruiter Matching Schemas
# ---------------------------------------------------------------------------


class RecruiterMatchExplanation(BaseModel):
    match_score: float = Field(..., ge=0, le=100)
    match_reasons: list[str] = Field(default_factory=list)
    role_alignment: str
    skill_overlap: list[str] = Field(default_factory=list)
    company_relevance: str
    active_opportunities_count: int = 0
    is_recommended: bool = True


class RecruiterMatchItem(BaseModel):
    recruiter: RecruiterProfileResponse
    match: RecruiterMatchExplanation
    crm_relationship_status: Optional[str] = None


class RecruiterDiscoveryResponse(BaseModel):
    total: int
    items: list[RecruiterMatchItem]
    verified_count: int
    companies_count: int


# ---------------------------------------------------------------------------
# Networking CRM Schemas
# ---------------------------------------------------------------------------

CRMRelationshipStatus = Literal[
    "discovered",
    "saved",
    "outreach_prepared",
    "contacted",
    "awaiting_response",
    "responded",
    "follow_up_required",
    "connected",
    "archived",
]


class NetworkingContactCreateRequest(BaseModel):
    recruiter_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    relationship_status: CRMRelationshipStatus = "saved"
    communication_channel: Optional[str] = None
    networking_notes: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)


class NetworkingContactUpdateRequest(BaseModel):
    relationship_status: Optional[CRMRelationshipStatus] = None
    communication_channel: Optional[str] = None
    response_status: Optional[
        Literal["pending", "positive", "neutral", "declined", "no_response"]
    ] = None
    networking_notes: Optional[str] = None
    next_follow_up_date: Optional[datetime] = None
    tags: Optional[list[str]] = None


class NetworkingActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    recruiter_id: uuid.UUID
    relationship_id: Optional[uuid.UUID] = None
    activity_type: str
    title: str
    description: Optional[str] = None
    created_at: datetime


class NetworkingContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    recruiter_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    relationship_status: str
    contact_source: str
    initial_contact_date: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    communication_channel: Optional[str] = None
    response_status: Optional[str] = None
    response_received_at: Optional[datetime] = None
    networking_notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    recruiter: Optional[RecruiterProfileResponse] = None
    recent_activities: list[NetworkingActivityResponse] = Field(default_factory=list)


class NetworkingCRMOverviewResponse(BaseModel):
    saved_recruiters_count: int
    companies_tracked_count: int
    outreach_messages_count: int
    pending_responses_count: int
    follow_ups_due_count: int
    contacts: list[NetworkingContactResponse]


# ---------------------------------------------------------------------------
# AI Outreach Assistant Schemas
# ---------------------------------------------------------------------------

OutreachMessageType = Literal[
    "linkedin_connection",
    "recruiter_intro",
    "job_inquiry",
    "internship_inquiry",
    "follow_up",
    "interview_thank_you",
    "networking_email",
]

OutreachTone = Literal["professional", "enthusiastic", "concise", "formal"]


class OutreachGenerateRequest(BaseModel):
    recruiter_id: uuid.UUID
    message_type: OutreachMessageType = "linkedin_connection"
    channel: Literal["linkedin", "email"] = "linkedin"
    tone: OutreachTone = "professional"
    job_id: Optional[uuid.UUID] = None
    resume_id: Optional[uuid.UUID] = None
    custom_instructions: Optional[str] = None
    enforce_linkedin_char_limit: bool = True  # Strict 300-char limit for connection note


class OutreachApproveRequest(BaseModel):
    edited_subject: Optional[str] = None
    edited_body: str = Field(..., min_length=10)


class OutreachSendGmailRequest(BaseModel):
    confirm_send: bool = Field(
        ...,
        description="Explicit candidate immediate confirmation is strictly required to send email.",
    )
    attach_resume: bool = True


class OutreachMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    recruiter_id: uuid.UUID
    relationship_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    message_type: str
    channel: str
    tone: str
    subject: Optional[str] = None
    body: str
    grounded_claims: list[str] = Field(default_factory=list)
    character_count: int
    status: str
    approval_confirmed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    sent_via_gmail: bool
    gmail_message_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Follow-up Intelligence Schemas
# ---------------------------------------------------------------------------


class FollowUpDueItem(BaseModel):
    relationship_id: uuid.UUID
    recruiter_id: uuid.UUID
    recruiter_name: str
    company_name: str
    communication_channel: Optional[str] = None
    relationship_status: str
    days_since_last_contact: int
    reason: str
    recommended_action: str
    suggested_message_type: OutreachMessageType


class FollowUpDueResponse(BaseModel):
    total_due: int
    items: list[FollowUpDueItem]
