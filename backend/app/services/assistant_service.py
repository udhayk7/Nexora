import contextlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.logging import logger
from app.core.storage import storage_service
from app.models.analysis import ResumeAnalysis
from app.models.application import ApplicationActivity, JobApplication
from app.models.assistant import (
    ApplicationEmail,
    ApplicationPreparation,
    CoverLetter,
)
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.assistant import (
    ApplicationEmailResponse,
    ApplicationQAResponse,
    CoverLetterResponse,
    PreparationResponse,
)
from app.services.ai.application_qa_engine import ApplicationQAEngine
from app.services.ai.cover_letter_engine import CoverLetterEngine
from app.services.ai.email_engine import EmailEngine
from app.services.cover_letter_pdf import compile_cover_letter_to_pdf
from app.services.gmail_service import GmailService

DEFAULT_CHECKLIST_TEMPLATE = [
    {
        "id": "review_requirements",
        "label": "Review core job requirements & technical stack",
        "completed": True,
        "required": True,
        "category": "research",
        "notes": None,
    },
    {
        "id": "select_resume",
        "label": "Select baseline resume version",
        "completed": False,
        "required": True,
        "category": "resume",
        "notes": None,
    },
    {
        "id": "tailor_resume",
        "label": "Tailor resume in Resume Tailoring Studio",
        "completed": False,
        "required": False,
        "category": "resume",
        "notes": None,
    },
    {
        "id": "generate_cover_letter",
        "label": "Generate job-specific grounded cover letter",
        "completed": False,
        "required": False,
        "category": "cover_letter",
        "notes": None,
    },
    {
        "id": "prepare_recruiter_email",
        "label": "Prepare outreach or direct application email",
        "completed": False,
        "required": False,
        "category": "outreach",
        "notes": None,
    },
    {
        "id": "review_qa_answers",
        "label": "Review grounded answers to application questions",
        "completed": False,
        "required": False,
        "category": "questions",
        "notes": None,
    },
    {
        "id": "open_official_portal",
        "label": "Open official career portal application link",
        "completed": False,
        "required": True,
        "category": "submission",
        "notes": None,
    },
    {
        "id": "confirm_submission",
        "label": "Explicitly confirm final application submission",
        "completed": False,
        "required": True,
        "category": "submission",
        "notes": None,
    },
]


class AssistantService:
    """Orchestrates application preparation, cover letters, outreach emails, and portal tracking."""

    @classmethod
    def get_or_create_preparation(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        application_id: Optional[uuid.UUID] = None,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> PreparationResponse:
        """Retrieve existing preparation session for the job or initialize with a checklist."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        prep = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )

        if not prep:
            # Resolve user's latest active resume version if not specified
            active_resume_id = None
            active_version_id = resume_version_id

            if not active_version_id:
                latest_resume = (
                    db.query(Resume)
                    .filter(Resume.user_id == user.id)
                    .order_by(Resume.created_at.desc())
                    .first()
                )
                if latest_resume and latest_resume.current_version_id:
                    active_resume_id = latest_resume.id
                    active_version_id = latest_resume.current_version_id

            # Initialize checklist template
            initial_checklist = [dict(item) for item in DEFAULT_CHECKLIST_TEMPLATE]
            if active_version_id:
                for item in initial_checklist:
                    if item["id"] == "select_resume":
                        item["completed"] = True

            prep = ApplicationPreparation(
                user_id=user.id,
                job_id=job_id,
                application_id=application_id,
                resume_id=active_resume_id,
                resume_version_id=active_version_id,
                checklist_status="in_progress" if active_version_id else "not_started",
                checklist_items=initial_checklist,
                qa_answers=[],
            )
            db.add(prep)
            db.commit()
            db.refresh(prep)

            audit_service.record_event(
                action="application_preparation.created",
                resource_type="application_preparation",
                actor_type="user",
                actor_id=str(user.id),
                resource_id=str(prep.id),
                metadata={"job_id": str(job_id)},
            )
        else:
            # Update application link if provided
            if application_id and prep.application_id != application_id:
                prep.application_id = application_id
                db.commit()
                db.refresh(prep)

        return PreparationResponse.model_validate(prep)

    @classmethod
    def update_preparation_checklist_item(
        cls,
        db: Session,
        user: User,
        preparation_id: uuid.UUID,
        item_id: str,
        completed: bool,
        notes: Optional[str] = None,
    ) -> PreparationResponse:
        """Toggle completion status and update notes for a checklist item."""
        prep = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.id == preparation_id,
                ApplicationPreparation.user_id == user.id,
            )
            .first()
        )
        if not prep:
            raise NotFoundError("Application preparation session not found")

        items = list(prep.checklist_items)
        found = False
        for item in items:
            if item.get("id") == item_id:
                item["completed"] = completed
                if notes is not None:
                    item["notes"] = notes
                found = True
                break

        if not found:
            items.append(
                {
                    "id": item_id,
                    "label": item_id.replace("_", " ").capitalize(),
                    "completed": completed,
                    "required": False,
                    "category": "custom",
                    "notes": notes,
                }
            )

        prep.checklist_items = items
        cls._recalculate_checklist_status(prep)
        db.commit()
        db.refresh(prep)
        return PreparationResponse.model_validate(prep)

    @classmethod
    def _recalculate_checklist_status(cls, prep: ApplicationPreparation) -> None:
        """Derive overall status (not_started, in_progress, ready_for_review, completed)."""
        items = prep.checklist_items
        if not items:
            prep.checklist_status = "not_started"
            return

        completed_count = sum(1 for i in items if i.get("completed"))
        required_items = [i for i in items if i.get("required", True)]
        all_required_done = (
            all(i.get("completed") for i in required_items) if required_items else False
        )

        if prep.submission_confirmed_at:
            prep.checklist_status = "completed"
        elif all_required_done:
            prep.checklist_status = "ready_for_review"
        elif completed_count > 0:
            prep.checklist_status = "in_progress"
        else:
            prep.checklist_status = "not_started"

    # =========================================================================
    # Cover Letter Management
    # =========================================================================

    @classmethod
    def generate_cover_letter(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        preparation_id: Optional[uuid.UUID] = None,
        resume_version_id: Optional[uuid.UUID] = None,
        user_instructions: Optional[str] = None,
    ) -> CoverLetterResponse:
        """Generate a job-specific cover letter with verbatim evidence grounding."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        # Resolve candidate resume & completed analysis
        version, analysis_result = cls._resolve_resume_and_analysis(db, user, resume_version_id)

        # Get existing version count for version numbering
        existing_count = (
            db.query(CoverLetter)
            .filter(CoverLetter.user_id == user.id, CoverLetter.job_id == job_id)
            .count()
        )
        next_ver = existing_count + 1

        # Run Cover Letter Engine
        cl_data, provider, model, is_fallback = CoverLetterEngine.generate_cover_letter(
            candidate_name=user.full_name,
            job=job,
            resume_analysis=analysis_result,
            user_instructions=user_instructions,
        )

        company_name = job.company.name if job.company else "Company"
        title = f"Cover Letter – {company_name} (v{next_ver})"

        letter = CoverLetter(
            user_id=user.id,
            job_id=job.id,
            preparation_id=preparation_id,
            resume_version_id=version.id if version else None,
            version_number=next_ver,
            title=title,
            content=cl_data.get("full_content", ""),
            opening=cl_data.get("opening"),
            body_paragraphs=cl_data.get("body_paragraphs", []),
            closing=cl_data.get("closing"),
            skill_alignment=cl_data.get("skill_alignment", []),
            experience_references=cl_data.get("experience_references", []),
            user_instructions=user_instructions,
            is_approved=False,
            provider=provider,
            model=model,
            is_deterministic_fallback=is_fallback,
        )
        db.add(letter)

        # Mark checklist item if preparation exists
        if preparation_id:
            prep = (
                db.query(ApplicationPreparation)
                .filter(ApplicationPreparation.id == preparation_id)
                .first()
            )
            if prep:
                items = list(prep.checklist_items)
                for item in items:
                    if item.get("id") == "generate_cover_letter":
                        item["completed"] = True
                prep.checklist_items = items
                cls._recalculate_checklist_status(prep)

        db.commit()
        db.refresh(letter)

        # Record audit and timeline
        audit_service.record_event(
            action="cover_letter.generated",
            resource_type="cover_letter",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(letter.id),
            metadata={
                "job_id": str(job.id),
                "version_number": next_ver,
                "provider": provider,
            },
        )
        cls._record_application_activity(
            db=db,
            user=user,
            job_id=job.id,
            activity_type="cover_letter_generated",
            title=f"Cover Letter Generated (v{next_ver})",
            description=f"Generated tailored cover letter for {job.title} at {company_name}.",
        )

        return CoverLetterResponse.model_validate(letter)

    @classmethod
    def update_cover_letter(
        cls,
        db: Session,
        user: User,
        letter_id: uuid.UUID,
        content: Optional[str] = None,
        title: Optional[str] = None,
        is_approved: Optional[bool] = None,
    ) -> CoverLetterResponse:
        """Edit or approve a cover letter."""
        letter = (
            db.query(CoverLetter)
            .filter(CoverLetter.id == letter_id, CoverLetter.user_id == user.id)
            .first()
        )
        if not letter:
            raise NotFoundError("Cover letter not found")

        if title is not None:
            letter.title = title
        if content is not None:
            letter.content = content
        if is_approved is not None:
            letter.is_approved = is_approved
            if is_approved:
                letter.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(letter)
        return CoverLetterResponse.model_validate(letter)

    @classmethod
    def get_cover_letter_pdf(
        cls,
        db: Session,
        user: User,
        letter_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Compile and return PDF bytes and filename for the cover letter."""
        letter = (
            db.query(CoverLetter)
            .filter(CoverLetter.id == letter_id, CoverLetter.user_id == user.id)
            .first()
        )
        if not letter:
            raise NotFoundError("Cover letter not found")

        job = db.query(Job).filter(Job.id == letter.job_id).first()
        company_name = job.company.name if job and job.company else "Company"
        role_title = job.title if job else "Software Engineer"

        pdf_bytes, _ = compile_cover_letter_to_pdf(
            candidate_name=user.full_name,
            candidate_email=user.email,
            company_name=company_name,
            role_title=role_title,
            content=letter.content,
        )

        filename = f"Cover_Letter_{company_name.replace(' ', '_')}_v{letter.version_number}.pdf"
        return pdf_bytes, filename

    # =========================================================================
    # Recruiter Email Management
    # =========================================================================

    @classmethod
    def generate_email(
        cls,
        db: Session,
        user: User,
        email_type: str,
        job_id: Optional[uuid.UUID] = None,
        application_id: Optional[uuid.UUID] = None,
        preparation_id: Optional[uuid.UUID] = None,
        resume_version_id: Optional[uuid.UUID] = None,
        cover_letter_id: Optional[uuid.UUID] = None,
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
    ) -> ApplicationEmailResponse:
        """Generate a personalized recruiter email."""
        job = db.query(Job).filter(Job.id == job_id).first() if job_id else None
        application = (
            db.query(JobApplication).filter(JobApplication.id == application_id).first()
            if application_id
            else None
        )

        # Candidate resume analysis
        analysis_result = None
        with contextlib.suppress(Exception):
            _, analysis_result = cls._resolve_resume_and_analysis(db, user, resume_version_id)

        email_data, provider, model, is_fallback = EmailEngine.generate_email(
            email_type=email_type,
            candidate_name=user.full_name,
            candidate_email=user.email,
            job=job,
            company_name=application.company_name if application else None,
            recipient_name=recipient_name or (application.recruiter_name if application else None),
            resume_analysis=analysis_result,
            user_instructions=user_instructions,
        )

        recip = recipient_email or (application.recruiter_email if application else None)

        email_rec = ApplicationEmail(
            user_id=user.id,
            job_id=job.id if job else (application.job_id if application else None),
            application_id=application_id,
            preparation_id=preparation_id,
            email_type=email_type,
            recipient_email=recip,
            recipient_name=recipient_name or (application.recruiter_name if application else None),
            subject=email_data.get("subject", "Job Application"),
            body=email_data.get("body", ""),
            status="draft",
            resume_version_id=resume_version_id,
            include_resume_attachment=True,
            cover_letter_id=cover_letter_id,
            include_cover_letter_attachment=bool(cover_letter_id),
            metadata_json={"provider": provider, "model": model, "is_fallback": is_fallback},
        )
        db.add(email_rec)

        if preparation_id:
            prep = (
                db.query(ApplicationPreparation)
                .filter(ApplicationPreparation.id == preparation_id)
                .first()
            )
            if prep:
                items = list(prep.checklist_items)
                for item in items:
                    if item.get("id") == "prepare_recruiter_email":
                        item["completed"] = True
                prep.checklist_items = items
                cls._recalculate_checklist_status(prep)

        db.commit()
        db.refresh(email_rec)

        audit_service.record_event(
            action="recruiter_email.generated",
            resource_type="application_email",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(email_rec.id),
            metadata={"email_type": email_type},
        )
        return ApplicationEmailResponse.model_validate(email_rec)

    @classmethod
    def update_email(
        cls,
        db: Session,
        user: User,
        email_id: uuid.UUID,
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        include_resume_attachment: Optional[bool] = None,
        resume_version_id: Optional[uuid.UUID] = None,
        include_cover_letter_attachment: Optional[bool] = None,
        cover_letter_id: Optional[uuid.UUID] = None,
    ) -> ApplicationEmailResponse:
        """Edit email details before approval."""
        email_rec = (
            db.query(ApplicationEmail)
            .filter(ApplicationEmail.id == email_id, ApplicationEmail.user_id == user.id)
            .first()
        )
        if not email_rec:
            raise NotFoundError("Email record not found")

        if recipient_email is not None:
            email_rec.recipient_email = recipient_email
        if recipient_name is not None:
            email_rec.recipient_name = recipient_name
        if subject is not None:
            email_rec.subject = subject
        if body is not None:
            email_rec.body = body
        if include_resume_attachment is not None:
            email_rec.include_resume_attachment = include_resume_attachment
        if resume_version_id is not None:
            email_rec.resume_version_id = resume_version_id
        if include_cover_letter_attachment is not None:
            email_rec.include_cover_letter_attachment = include_cover_letter_attachment
        if cover_letter_id is not None:
            email_rec.cover_letter_id = cover_letter_id

        db.commit()
        db.refresh(email_rec)
        return ApplicationEmailResponse.model_validate(email_rec)

    @classmethod
    def approve_email(
        cls,
        db: Session,
        user: User,
        email_id: uuid.UUID,
    ) -> ApplicationEmailResponse:
        """Approve an email draft for dispatch."""
        email_rec = (
            db.query(ApplicationEmail)
            .filter(ApplicationEmail.id == email_id, ApplicationEmail.user_id == user.id)
            .first()
        )
        if not email_rec:
            raise NotFoundError("Email record not found")

        email_rec.status = "approved"
        email_rec.approval_confirmed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(email_rec)

        audit_service.record_event(
            action="recruiter_email.approved",
            resource_type="application_email",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(email_rec.id),
        )
        return ApplicationEmailResponse.model_validate(email_rec)

    @classmethod
    def create_gmail_draft(
        cls,
        db: Session,
        user: User,
        email_id: uuid.UUID,
    ) -> ApplicationEmailResponse:
        """Create a draft in the user's connected Gmail account."""
        email_rec = (
            db.query(ApplicationEmail)
            .filter(ApplicationEmail.id == email_id, ApplicationEmail.user_id == user.id)
            .first()
        )
        if not email_rec:
            raise NotFoundError("Email record not found")

        if not email_rec.recipient_email:
            raise BadRequestError("Cannot create Gmail draft without an explicit recipient email.")

        # Prepare attachments
        attachments = cls._prepare_email_attachments(db, user, email_rec)

        draft_result = GmailService.create_draft(
            db=db,
            user=user,
            recipient_email=email_rec.recipient_email,
            subject=email_rec.subject,
            body=email_rec.body,
            attachments=attachments,
        )

        email_rec.gmail_draft_id = draft_result.get("draft_id")
        email_rec.gmail_message_id = draft_result.get("message_id")
        email_rec.gmail_thread_id = draft_result.get("thread_id")
        db.commit()
        db.refresh(email_rec)

        # Audit and timeline
        audit_service.record_event(
            action="gmail.draft_created",
            resource_type="application_email",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(email_rec.id),
            metadata={"draft_id": email_rec.gmail_draft_id},
        )
        cls._record_application_activity(
            db=db,
            user=user,
            job_id=email_rec.job_id,
            activity_type="gmail_draft_created",
            title="Gmail Draft Created",
            description=f"Created Gmail draft for '{email_rec.subject}'.",
        )
        return ApplicationEmailResponse.model_validate(email_rec)

    @classmethod
    def send_email_message(
        cls,
        db: Session,
        user: User,
        email_id: uuid.UUID,
        confirm_send: bool,
        idempotency_key: Optional[str] = None,
    ) -> ApplicationEmailResponse:
        """Send approved email via Gmail after explicit user confirmation."""
        if not confirm_send:
            raise ForbiddenError(
                "Explicit user confirmation is strictly required immediately before sending."
            )

        email_rec = (
            db.query(ApplicationEmail)
            .filter(ApplicationEmail.id == email_id, ApplicationEmail.user_id == user.id)
            .first()
        )
        if not email_rec:
            raise NotFoundError("Email record not found")

        # Prevent accidental duplicate sends
        if email_rec.status == "sent":
            raise BadRequestError(
                f"This email was already sent on {email_rec.sent_at}. Duplicate sends are blocked."
            )

        if not email_rec.recipient_email:
            raise BadRequestError(
                "Recipient email is required. Nexora never sends to guessed emails."
            )

        # Prepare attachments
        attachments = cls._prepare_email_attachments(db, user, email_rec)

        send_result = GmailService.send_email(
            db=db,
            user=user,
            recipient_email=email_rec.recipient_email,
            subject=email_rec.subject,
            body=email_rec.body,
            confirm_send=confirm_send,
            attachments=attachments,
        )

        email_rec.status = "sent"
        email_rec.send_confirmed_at = datetime.now(timezone.utc)
        email_rec.sent_at = datetime.now(timezone.utc)
        email_rec.gmail_message_id = send_result.get("message_id")
        email_rec.gmail_thread_id = send_result.get("thread_id")
        db.commit()
        db.refresh(email_rec)

        # Audit and timeline
        audit_service.record_event(
            action="gmail.email_sent",
            resource_type="application_email",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(email_rec.id),
            metadata={
                "message_id": email_rec.gmail_message_id,
                "recipient": email_rec.recipient_email,
            },
        )
        cls._record_application_activity(
            db=db,
            user=user,
            job_id=email_rec.job_id,
            activity_type="email_sent",
            title="Email Sent via Gmail",
            description=(
                f"Sent '{email_rec.subject}' to {email_rec.recipient_email} "
                f"(ID: {email_rec.gmail_message_id})."
            ),
        )
        return ApplicationEmailResponse.model_validate(email_rec)

    # =========================================================================
    # Application Q&A
    # =========================================================================

    @classmethod
    def generate_application_qa(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        preparation_id: Optional[uuid.UUID] = None,
        resume_version_id: Optional[uuid.UUID] = None,
        custom_questions: Optional[list[str]] = None,
    ) -> ApplicationQAResponse:
        """Generate answers to application questions grounded in resume evidence."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        _, analysis_result = cls._resolve_resume_and_analysis(db, user, resume_version_id)

        qa_items = ApplicationQAEngine.generate(
            job=job,
            resume_analysis=analysis_result,
            custom_questions=custom_questions,
        )

        if preparation_id:
            prep = (
                db.query(ApplicationPreparation)
                .filter(ApplicationPreparation.id == preparation_id)
                .first()
            )
            if prep:
                prep.qa_answers = [item.model_dump() for item in qa_items]
                items = list(prep.checklist_items)
                for item in items:
                    if item.get("id") == "review_qa_answers":
                        item["completed"] = True
                prep.checklist_items = items
                cls._recalculate_checklist_status(prep)
                db.commit()

        return ApplicationQAResponse(
            job_id=job.id,
            preparation_id=preparation_id,
            resume_version_id=resume_version_id,
            items=qa_items,
        )

    # =========================================================================
    # External Portal Assistance
    # =========================================================================

    @classmethod
    def record_portal_opened(
        cls,
        db: Session,
        user: User,
        preparation_id: uuid.UUID,
    ) -> PreparationResponse:
        """Record that the user opened the external job application portal link.

        NOTE: Opening the portal link NEVER marks the application as submitted.
        """
        prep = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.id == preparation_id,
                ApplicationPreparation.user_id == user.id,
            )
            .first()
        )
        if not prep:
            raise NotFoundError("Application preparation session not found")

        prep.portal_opened_at = datetime.now(timezone.utc)
        items = list(prep.checklist_items)
        for item in items:
            if item.get("id") == "open_official_portal":
                item["completed"] = True
        prep.checklist_items = items
        cls._recalculate_checklist_status(prep)
        db.commit()
        db.refresh(prep)

        audit_service.record_event(
            action="application_portal.opened",
            resource_type="application_preparation",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(prep.id),
        )
        cls._record_application_activity(
            db=db,
            user=user,
            job_id=prep.job_id,
            activity_type="portal_opened",
            title="External Application Portal Opened",
            description="Applicant opened the official career portal link to prepare submission.",
        )
        return PreparationResponse.model_validate(prep)

    @classmethod
    def confirm_portal_submission(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        preparation_id: Optional[uuid.UUID] = None,
        application_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> PreparationResponse:
        """Explicitly confirm that the user completed and submitted their external application."""
        prep = None
        if preparation_id:
            prep = (
                db.query(ApplicationPreparation)
                .filter(
                    ApplicationPreparation.id == preparation_id,
                    ApplicationPreparation.user_id == user.id,
                )
                .first()
            )
        else:
            prep = (
                db.query(ApplicationPreparation)
                .filter(
                    ApplicationPreparation.job_id == job_id,
                    ApplicationPreparation.user_id == user.id,
                )
                .first()
            )

        if not prep:
            raise NotFoundError("Application preparation session not found")

        now = datetime.now(timezone.utc)
        prep.submission_confirmed_at = now
        prep.checklist_status = "completed"

        items = list(prep.checklist_items)
        for item in items:
            if item.get("id") == "confirm_submission":
                item["completed"] = True
        prep.checklist_items = items

        # Also update JobApplication if linked
        app_rec = None
        if prep.application_id:
            app_rec = (
                db.query(JobApplication).filter(JobApplication.id == prep.application_id).first()
            )
        elif application_id:
            app_rec = db.query(JobApplication).filter(JobApplication.id == application_id).first()

        if app_rec:
            app_rec.submission_confirmed = True
            app_rec.applied_at = now
            if app_rec.status in ("interested", "preparing"):
                app_rec.status = "applied"

        db.commit()
        db.refresh(prep)

        audit_service.record_event(
            action="application.submission_confirmed",
            resource_type="application_preparation",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(prep.id),
            metadata={"notes": notes},
        )
        cls._record_application_activity(
            db=db,
            user=user,
            job_id=job_id,
            activity_type="application_submitted",
            title="Application Submission Confirmed",
            description="Applicant explicitly confirmed external submission was completed.",
        )
        return PreparationResponse.model_validate(prep)

    # =========================================================================
    # Helpers
    # =========================================================================

    @classmethod
    def _prepare_email_attachments(
        cls,
        db: Session,
        user: User,
        email_rec: ApplicationEmail,
    ) -> list[tuple[str, bytes, str]]:
        """Retrieve and validate approved resume and cover letter PDF attachments."""
        attachments: list[tuple[str, bytes, str]] = []

        # 1. Resume attachment
        if email_rec.include_resume_attachment:
            ver_id = email_rec.resume_version_id
            if not ver_id:
                # Fallback to user's latest resume version
                latest_resume = (
                    db.query(Resume)
                    .filter(Resume.user_id == user.id)
                    .order_by(Resume.created_at.desc())
                    .first()
                )
                if latest_resume and latest_resume.current_version_id:
                    ver_id = latest_resume.current_version_id

            if ver_id:
                version = (
                    db.query(ResumeVersion)
                    .join(Resume, Resume.id == ResumeVersion.resume_id)
                    .filter(ResumeVersion.id == ver_id, Resume.user_id == user.id)
                    .first()
                )
                if version:
                    try:
                        content_bytes = storage_service.get_file(version.storage_path)
                        safe_name = f"Resume_{user.full_name.replace(' ', '_')}.pdf"
                        attachments.append((safe_name, content_bytes, "application/pdf"))
                    except Exception as exc:
                        logger.warning(
                            "Could not read resume file %s: %s", version.storage_path, exc
                        )

        # 2. Cover Letter attachment
        if email_rec.include_cover_letter_attachment and email_rec.cover_letter_id:
            letter = (
                db.query(CoverLetter)
                .filter(CoverLetter.id == email_rec.cover_letter_id, CoverLetter.user_id == user.id)
                .first()
            )
            if letter:
                job = db.query(Job).filter(Job.id == letter.job_id).first()
                company_name = job.company.name if job and job.company else "Company"
                role_title = job.title if job else "Software Engineer"
                cl_pdf_bytes, _ = compile_cover_letter_to_pdf(
                    candidate_name=user.full_name,
                    candidate_email=user.email,
                    company_name=company_name,
                    role_title=role_title,
                    content=letter.content,
                )
                safe_name = f"Cover_Letter_{company_name.replace(' ', '_')}.pdf"
                attachments.append((safe_name, cl_pdf_bytes, "application/pdf"))

        return attachments

    @classmethod
    def _resolve_resume_and_analysis(
        cls,
        db: Session,
        user: User,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> tuple[Optional[ResumeVersion], ResumeAnalysisResult]:
        """Resolve candidate resume version and parsed AI analysis."""
        version: Optional[ResumeVersion] = None
        if resume_version_id:
            version = (
                db.query(ResumeVersion)
                .join(Resume, Resume.id == ResumeVersion.resume_id)
                .filter(ResumeVersion.id == resume_version_id, Resume.user_id == user.id)
                .first()
            )
            if not version:
                raise NotFoundError("Requested resume version not found")
        else:
            latest_resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if latest_resume and latest_resume.current_version_id:
                version = (
                    db.query(ResumeVersion)
                    .filter(ResumeVersion.id == latest_resume.current_version_id)
                    .first()
                )

        if not version:
            raise BadRequestError(
                "No resume found. Please upload a resume before using the Application Assistant."
            )

        analysis = (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.version_id == version.id,
                ResumeAnalysis.status == "completed",
            )
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
        if not analysis:
            raise BadRequestError(
                "Resume has not been analyzed yet. Please run AI analysis on your resume first."
            )

        return version, ResumeAnalysisResult.model_validate(analysis.result)

    @classmethod
    def _record_application_activity(
        cls,
        db: Session,
        user: User,
        job_id: Optional[uuid.UUID],
        activity_type: str,
        title: str,
        description: str,
    ) -> None:
        """Helper to append an activity event to any linked JobApplication."""
        if not job_id:
            return

        app_rec = (
            db.query(JobApplication)
            .filter(JobApplication.job_id == job_id, JobApplication.user_id == user.id)
            .first()
        )
        if not app_rec:
            return

        act = ApplicationActivity(
            application_id=app_rec.id,
            user_id=user.id,
            activity_type=activity_type,
            title=title,
            description=description,
            activity_date=datetime.now(timezone.utc),
            metadata_json={},
        )
        db.add(act)
        db.commit()
