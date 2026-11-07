import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Google OAuth & Gmail Integration
# ============================================================================


class GoogleAuthUrlResponse(BaseModel):
    """URL to initiate official Google OAuth 2.0 authorization."""

    authorization_url: str
    state: str


class GoogleOAuthCallbackRequest(BaseModel):
    """Payload received from Google OAuth callback."""

    code: str
    state: str


class GmailConnectionStatusResponse(BaseModel):
    """Public Gmail connection status. Never exposes tokens or secrets."""

    is_connected: bool
    email: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: Optional[datetime] = None
    is_token_valid: bool = False


# ============================================================================
# Application Preparation & Checklist
# ============================================================================


class ChecklistItem(BaseModel):
    """A single checklist task in application preparation."""

    id: str
    label: str
    completed: bool = False
    required: bool = True
    category: str = "general"
    notes: Optional[str] = None


class PreparationCreateRequest(BaseModel):
    """Initialize or load application preparation for a job."""

    job_id: uuid.UUID
    application_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None


class ChecklistItemUpdateRequest(BaseModel):
    """Update completed state or notes of a checklist item."""

    item_id: str
    completed: bool
    notes: Optional[str] = None


class PreparationUpdateRequest(BaseModel):
    """Update checklist items, notes, or resume version for preparation."""

    resume_version_id: Optional[uuid.UUID] = None
    checklist_status: Optional[str] = None
    checklist_items: Optional[list[ChecklistItem]] = None
    notes: Optional[str] = None


class PreparationResponse(BaseModel):
    """Full application preparation session state."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    application_id: Optional[uuid.UUID] = None
    resume_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    checklist_status: str
    checklist_items: list[dict[str, Any]] = Field(default_factory=list)
    qa_answers: list[dict[str, Any]] = Field(default_factory=list)
    portal_opened_at: Optional[datetime] = None
    submission_confirmed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# AI Cover Letter
# ============================================================================


class CoverLetterGenerateRequest(BaseModel):
    """Request to generate a job-specific grounded cover letter."""

    job_id: uuid.UUID
    preparation_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    user_instructions: Optional[str] = Field(
        None, max_length=1500, description="Optional tone, focus, or project preference"
    )


class CoverLetterUpdateRequest(BaseModel):
    """Update or edit cover letter text and approval state."""

    title: Optional[str] = None
    content: Optional[str] = None
    is_approved: Optional[bool] = None


class CoverLetterResponse(BaseModel):
    """Generated or customized cover letter with citation grounding."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    preparation_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    version_number: int
    title: str
    content: str
    opening: Optional[str] = None
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: Optional[str] = None
    skill_alignment: list[str] = Field(default_factory=list)
    experience_references: list[dict[str, Any]] = Field(default_factory=list)
    user_instructions: Optional[str] = None
    is_approved: bool
    approved_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    is_deterministic_fallback: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Recruiter Email & Gmail Workflow
# ============================================================================


class EmailGenerateRequest(BaseModel):
    """Request to generate a personalized recruiter or application email."""

    job_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    preparation_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    cover_letter_id: Optional[uuid.UUID] = None
    email_type: str = Field(
        ...,
        description=(
            "direct_application, recruiter_outreach, referral_request, "
            "follow_up, interview_follow_up, thank_you"
        ),
    )
    recipient_email: Optional[str] = Field(
        None, description="Explicit recipient email. Nexora will never guess or infer emails."
    )
    recipient_name: Optional[str] = None
    user_instructions: Optional[str] = Field(None, max_length=1000)


class EmailUpdateRequest(BaseModel):
    """Edit recipient, subject, body, or attachments before approval."""

    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    include_resume_attachment: Optional[bool] = None
    resume_version_id: Optional[uuid.UUID] = None
    include_cover_letter_attachment: Optional[bool] = None
    cover_letter_id: Optional[uuid.UUID] = None


class EmailApproveRequest(BaseModel):
    """Approve an email draft for sending or Gmail draft creation."""

    is_approved: bool = True


class GmailDraftCreateRequest(BaseModel):
    """Create a draft in the user's connected Gmail account."""

    email_id: Optional[uuid.UUID] = None


class EmailSendRequest(BaseModel):
    """Send an approved email through the connected Gmail account."""

    email_id: Optional[uuid.UUID] = None
    confirm_send: bool = Field(
        ...,
        description="Explicit user confirmation immediately before dispatch. Mandatory true.",
    )
    idempotency_key: Optional[str] = Field(
        None, description="Optional unique key to prevent accidental duplicate dispatch"
    )


class ApplicationEmailResponse(BaseModel):
    """Personalized email record and its Gmail integration status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    preparation_id: Optional[uuid.UUID] = None
    email_type: str
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: str
    body: str
    status: str
    approval_confirmed_at: Optional[datetime] = None
    send_confirmed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    gmail_draft_id: Optional[str] = None
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    resume_version_id: Optional[uuid.UUID] = None
    include_resume_attachment: bool
    cover_letter_id: Optional[uuid.UUID] = None
    include_cover_letter_attachment: bool
    error_message: Optional[str] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Application Q&A
# ============================================================================


class QAItem(BaseModel):
    """A generated question and answer pair grounded in resume evidence."""

    question: str
    answer: str
    grounded_evidence: list[str] = Field(default_factory=list)
    confidence: str = "high"  # high, medium, low
    missing_info: Optional[str] = None  # Explicitly flags what candidate must provide


class ApplicationQAGenerateRequest(BaseModel):
    """Request to generate answers to standard or custom application questions."""

    job_id: uuid.UUID
    preparation_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    custom_questions: Optional[list[str]] = None


class ApplicationQAResponse(BaseModel):
    """Grounded answers to application questions."""

    job_id: uuid.UUID
    preparation_id: Optional[uuid.UUID] = None
    resume_version_id: Optional[uuid.UUID] = None
    items: list[QAItem]


# ============================================================================
# External Portal Submission Confirmation
# ============================================================================


class PortalSubmitConfirmationRequest(BaseModel):
    """Explicit confirmation from user that an external application portal was submitted."""

    job_id: uuid.UUID
    preparation_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
