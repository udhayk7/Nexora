import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.assistant import ApplicationEmail, CoverLetter
from app.models.user import User
from app.schemas.assistant import (
    ApplicationEmailResponse,
    ApplicationQAGenerateRequest,
    ApplicationQAResponse,
    ChecklistItemUpdateRequest,
    CoverLetterGenerateRequest,
    CoverLetterResponse,
    CoverLetterUpdateRequest,
    EmailApproveRequest,
    EmailGenerateRequest,
    EmailSendRequest,
    EmailUpdateRequest,
    PortalSubmitConfirmationRequest,
    PreparationCreateRequest,
    PreparationResponse,
)
from app.services.assistant_service import AssistantService

router = APIRouter(prefix="/application-assistant", tags=["AI Application Assistant"])


# ============================================================================
# Preparation Workspace & Checklist Endpoints
# ============================================================================


@router.post(
    "/preparations",
    response_model=PreparationResponse,
    summary="Initialize or retrieve application preparation session",
)
def get_or_create_preparation(
    data: PreparationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationResponse:
    """Retrieve existing preparation session for a job or create a new session."""
    return AssistantService.get_or_create_preparation(
        db=db,
        user=current_user,
        job_id=data.job_id,
        application_id=data.application_id,
        resume_version_id=data.resume_version_id,
    )


@router.get(
    "/preparations/{preparation_id}",
    response_model=PreparationResponse,
    summary="Get application preparation details",
)
def get_preparation_by_id(
    preparation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationResponse:
    """Get active preparation workspace session by ID."""
    from app.models.assistant import ApplicationPreparation

    prep = (
        db.query(ApplicationPreparation)
        .filter(
            ApplicationPreparation.id == preparation_id,
            ApplicationPreparation.user_id == current_user.id,
        )
        .first()
    )
    if not prep:
        raise NotFoundError("Application preparation session not found")
    return PreparationResponse.model_validate(prep)


@router.patch(
    "/preparations/{preparation_id}/checklist",
    response_model=PreparationResponse,
    summary="Update checklist item completion status",
)
def update_checklist_item(
    preparation_id: uuid.UUID,
    data: ChecklistItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationResponse:
    """Toggle completion and update notes on a preparation checklist item."""
    return AssistantService.update_preparation_checklist_item(
        db=db,
        user=current_user,
        preparation_id=preparation_id,
        item_id=data.item_id,
        completed=data.completed,
        notes=data.notes,
    )


@router.post(
    "/preparations/{preparation_id}/portal-opened",
    response_model=PreparationResponse,
    summary="Record external application portal link opened",
)
def record_portal_opened(
    preparation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationResponse:
    """Record that user opened portal URL. NOTE: This never marks application as submitted."""
    return AssistantService.record_portal_opened(
        db=db, user=current_user, preparation_id=preparation_id
    )


@router.post(
    "/preparations/confirm-submission",
    response_model=PreparationResponse,
    summary="Explicitly confirm external application portal submission",
)
def confirm_portal_submission(
    data: PortalSubmitConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationResponse:
    """Explicit user confirmation that external application portal submission was completed."""
    return AssistantService.confirm_portal_submission(
        db=db,
        user=current_user,
        job_id=data.job_id,
        preparation_id=data.preparation_id,
        application_id=data.application_id,
        notes=data.notes,
    )


# ============================================================================
# Cover Letter Endpoints
# ============================================================================


@router.post(
    "/cover-letters/generate",
    response_model=CoverLetterResponse,
    summary="Generate job-specific grounded cover letter",
)
def generate_cover_letter(
    data: CoverLetterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoverLetterResponse:
    """Generate an evidence-grounded cover letter tailored to the target job opportunity."""
    return AssistantService.generate_cover_letter(
        db=db,
        user=current_user,
        job_id=data.job_id,
        preparation_id=data.preparation_id,
        resume_version_id=data.resume_version_id,
        user_instructions=data.user_instructions,
    )


@router.get(
    "/cover-letters/{letter_id}",
    response_model=CoverLetterResponse,
    summary="Get cover letter details",
)
def get_cover_letter(
    letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoverLetterResponse:
    """Retrieve an existing cover letter."""
    letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.id == letter_id, CoverLetter.user_id == current_user.id)
        .first()
    )
    if not letter:
        raise NotFoundError("Cover letter not found")
    return CoverLetterResponse.model_validate(letter)


@router.patch(
    "/cover-letters/{letter_id}",
    response_model=CoverLetterResponse,
    summary="Edit or approve cover letter",
)
def update_cover_letter(
    letter_id: uuid.UUID,
    data: CoverLetterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoverLetterResponse:
    """Edit cover letter content, title, or approval state."""
    return AssistantService.update_cover_letter(
        db=db,
        user=current_user,
        letter_id=letter_id,
        content=data.content,
        title=data.title,
        is_approved=data.is_approved,
    )


@router.get(
    "/cover-letters/{letter_id}/pdf",
    summary="Download cover letter as PDF",
)
def download_cover_letter_pdf(
    letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Compile and download the cover letter as a formatted PDF."""
    pdf_bytes, filename = AssistantService.get_cover_letter_pdf(
        db=db, user=current_user, letter_id=letter_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/jobs/{job_id}/cover-letters",
    response_model=list[CoverLetterResponse],
    summary="List cover letter versions for a job",
)
def list_cover_letters_for_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CoverLetterResponse]:
    """Retrieve all cover letter versions generated for a job."""
    letters = (
        db.query(CoverLetter)
        .filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.version_number.desc())
        .all()
    )
    return [CoverLetterResponse.model_validate(letter) for letter in letters]


# ============================================================================
# Recruiter Email & Gmail Endpoints
# ============================================================================


@router.post(
    "/emails/generate",
    response_model=ApplicationEmailResponse,
    summary="Generate personalized recruiter email",
)
def generate_email(
    data: EmailGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Generate outreach, application, follow-up, or thank-you email."""
    return AssistantService.generate_email(
        db=db,
        user=current_user,
        email_type=data.email_type,
        job_id=data.job_id,
        application_id=data.application_id,
        preparation_id=data.preparation_id,
        resume_version_id=data.resume_version_id,
        cover_letter_id=data.cover_letter_id,
        recipient_email=data.recipient_email,
        recipient_name=data.recipient_name,
        user_instructions=data.user_instructions,
    )


@router.get(
    "/emails/{email_id}",
    response_model=ApplicationEmailResponse,
    summary="Get email details",
)
def get_email_by_id(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Get email record by ID."""
    email_rec = (
        db.query(ApplicationEmail)
        .filter(ApplicationEmail.id == email_id, ApplicationEmail.user_id == current_user.id)
        .first()
    )
    if not email_rec:
        raise NotFoundError("Email record not found")
    return ApplicationEmailResponse.model_validate(email_rec)


@router.patch(
    "/emails/{email_id}",
    response_model=ApplicationEmailResponse,
    summary="Edit email details before dispatch",
)
def update_email_details(
    email_id: uuid.UUID,
    data: EmailUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Edit recipient, subject, body, or attachments for an email."""
    return AssistantService.update_email(
        db=db,
        user=current_user,
        email_id=email_id,
        recipient_email=data.recipient_email,
        recipient_name=data.recipient_name,
        subject=data.subject,
        body=data.body,
        include_resume_attachment=data.include_resume_attachment,
        resume_version_id=data.resume_version_id,
        include_cover_letter_attachment=data.include_cover_letter_attachment,
        cover_letter_id=data.cover_letter_id,
    )


@router.post(
    "/emails/{email_id}/approve",
    response_model=ApplicationEmailResponse,
    summary="Approve an email draft",
)
def approve_email_draft(
    email_id: uuid.UUID,
    data: EmailApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Mark email draft approved for draft creation or sending."""
    return AssistantService.approve_email(db=db, user=current_user, email_id=email_id)


@router.post(
    "/emails/{email_id}/gmail-draft",
    response_model=ApplicationEmailResponse,
    summary="Create draft in connected Gmail account",
)
def create_gmail_draft_endpoint(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Create a draft in user's connected Gmail account with optional PDF attachments."""
    return AssistantService.create_gmail_draft(db=db, user=current_user, email_id=email_id)


@router.post(
    "/emails/{email_id}/send",
    response_model=ApplicationEmailResponse,
    summary="Send approved email via connected Gmail account",
)
def send_email_endpoint(
    email_id: uuid.UUID,
    data: EmailSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationEmailResponse:
    """Dispatch email via user's connected Gmail account with explicit confirmation."""
    return AssistantService.send_email_message(
        db=db,
        user=current_user,
        email_id=email_id,
        confirm_send=data.confirm_send,
        idempotency_key=data.idempotency_key,
    )


@router.get(
    "/jobs/{job_id}/emails",
    response_model=list[ApplicationEmailResponse],
    summary="List emails for a job",
)
def list_emails_for_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationEmailResponse]:
    """Retrieve all recruiter and outreach emails prepared for a job."""
    emails = (
        db.query(ApplicationEmail)
        .filter(ApplicationEmail.job_id == job_id, ApplicationEmail.user_id == current_user.id)
        .order_by(ApplicationEmail.created_at.desc())
        .all()
    )
    return [ApplicationEmailResponse.model_validate(e) for e in emails]


# ============================================================================
# Application Q&A Endpoints
# ============================================================================


@router.post(
    "/qa/generate",
    response_model=ApplicationQAResponse,
    summary="Generate grounded answers to application questions",
)
def generate_application_qa(
    data: ApplicationQAGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationQAResponse:
    """Generate truthful, grounded answers to common or custom application questions."""
    return AssistantService.generate_application_qa(
        db=db,
        user=current_user,
        job_id=data.job_id,
        preparation_id=data.preparation_id,
        resume_version_id=data.resume_version_id,
        custom_questions=data.custom_questions,
    )
