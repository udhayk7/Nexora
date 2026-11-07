import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.models.job import Job
from app.models.networking import (
    NetworkingActivity,
    NetworkingContact,
    NetworkingOutreachMessage,
    RecruiterProfile,
)
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.networking import (
    FollowUpDueItem,
    FollowUpDueResponse,
    NetworkingContactCreateRequest,
    NetworkingContactResponse,
    NetworkingContactUpdateRequest,
    NetworkingCRMOverviewResponse,
    OutreachApproveRequest,
    OutreachGenerateRequest,
    RecruiterProfileResponse,
)
from app.services.ai.networking_outreach_engine import NetworkingOutreachEngine
from app.services.gmail_service import GmailService

logger = logging.getLogger("nexora.services.networking_crm")


class NetworkingCRMService:
    """Manages the candidate networking CRM, outreach lifecycles, and follow-up intelligence."""

    @classmethod
    def get_or_create_contact(
        cls,
        db: Session,
        user: User,
        data: NetworkingContactCreateRequest,
    ) -> NetworkingContact:
        """Add recruiter to candidate's CRM or return existing relationship (deduplication)."""
        recruiter = (
            db.query(RecruiterProfile).filter(RecruiterProfile.id == data.recruiter_id).first()
        )
        if not recruiter:
            raise NotFoundError(f"Recruiter with ID {data.recruiter_id} not found.")

        existing = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.user_id == user.id,
                NetworkingContact.recruiter_id == data.recruiter_id,
            )
            .first()
        )
        if existing:
            if (
                data.relationship_status
                and existing.relationship_status != data.relationship_status
            ):
                existing.relationship_status = data.relationship_status
            if data.networking_notes:
                existing.networking_notes = (
                    (existing.networking_notes or "") + f"\n{data.networking_notes}"
                ).strip()
            db.commit()
            db.refresh(existing)
            return existing

        contact = NetworkingContact(
            id=uuid.uuid4(),
            user_id=user.id,
            recruiter_id=data.recruiter_id,
            company_id=data.company_id or recruiter.company_id,
            job_id=data.job_id,
            application_id=data.application_id,
            relationship_status=data.relationship_status or "saved",
            contact_source="recruiter_discovery",
            communication_channel=data.communication_channel,
            networking_notes=data.networking_notes,
            next_follow_up_date=data.next_follow_up_date,
            tags=data.tags or [],
        )
        db.add(contact)
        db.flush()

        # Log initial activity
        activity = NetworkingActivity(
            id=uuid.uuid4(),
            user_id=user.id,
            recruiter_id=data.recruiter_id,
            relationship_id=contact.id,
            activity_type="status_change",
            title="Recruiter Saved to CRM",
            description=(
                f"Saved {recruiter.full_name} ({recruiter.company_name}) to networking contacts."
            ),
        )
        db.add(activity)

        db.commit()
        db.refresh(contact)

        audit_service.record_event(
            action="networking_contact.created",
            resource_type="networking_contact",
            resource_id=str(contact.id),
            actor_type="user",
            actor_id=str(user.id),
            metadata={"recruiter_id": str(recruiter.id), "status": contact.relationship_status},
        )
        return contact

    @classmethod
    def update_contact(
        cls,
        db: Session,
        user: User,
        relationship_id: uuid.UUID,
        data: NetworkingContactUpdateRequest,
    ) -> NetworkingContact:
        contact = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.id == relationship_id,
                NetworkingContact.user_id == user.id,
            )
            .first()
        )
        if not contact:
            raise NotFoundError(f"Networking contact {relationship_id} not found.")

        old_status = contact.relationship_status
        now = datetime.now(timezone.utc)

        if data.relationship_status is not None:
            contact.relationship_status = data.relationship_status
            if data.relationship_status == "contacted":
                if not contact.initial_contact_date:
                    contact.initial_contact_date = now
                contact.last_contact_date = now

            # Log status change activity
            act = NetworkingActivity(
                id=uuid.uuid4(),
                user_id=user.id,
                recruiter_id=contact.recruiter_id,
                relationship_id=contact.id,
                activity_type="status_change",
                title="Relationship Status Updated",
                description=f"Status changed from '{old_status}' to '{data.relationship_status}'.",
            )
            db.add(act)

        if data.communication_channel is not None:
            contact.communication_channel = data.communication_channel
        if data.response_status is not None:
            contact.response_status = data.response_status
            contact.response_received_at = now
            if data.response_status in ("positive", "neutral"):
                contact.relationship_status = "responded"
            act_resp = NetworkingActivity(
                id=uuid.uuid4(),
                user_id=user.id,
                recruiter_id=contact.recruiter_id,
                relationship_id=contact.id,
                activity_type="response_recorded",
                title="Recruiter Response Recorded",
                description=f"Candidate recorded response: {data.response_status}.",
            )
            db.add(act_resp)

        if data.networking_notes is not None:
            contact.networking_notes = data.networking_notes
            act_note = NetworkingActivity(
                id=uuid.uuid4(),
                user_id=user.id,
                recruiter_id=contact.recruiter_id,
                relationship_id=contact.id,
                activity_type="note_added",
                title="Notes Updated",
                description="Networking notes updated.",
            )
            db.add(act_note)

        if data.next_follow_up_date is not None:
            contact.next_follow_up_date = data.next_follow_up_date
            act_fl = NetworkingActivity(
                id=uuid.uuid4(),
                user_id=user.id,
                recruiter_id=contact.recruiter_id,
                relationship_id=contact.id,
                activity_type="follow_up_scheduled",
                title="Follow-Up Scheduled",
                description=(
                    f"Next follow-up date set for {data.next_follow_up_date.strftime('%Y-%m-%d')}."
                ),
            )
            db.add(act_fl)

        if data.tags is not None:
            contact.tags = data.tags

        db.commit()
        db.refresh(contact)
        return contact

    @classmethod
    def get_crm_overview(cls, db: Session, user: User) -> NetworkingCRMOverviewResponse:
        contacts = (
            db.query(NetworkingContact)
            .filter(NetworkingContact.user_id == user.id)
            .order_by(NetworkingContact.updated_at.desc())
            .all()
        )

        now = datetime.now(timezone.utc)
        saved_count = len(contacts)
        unique_companies = len({c.company_id for c in contacts if c.company_id})
        outreach_count = (
            db.query(NetworkingOutreachMessage)
            .filter(NetworkingOutreachMessage.user_id == user.id)
            .count()
        )
        pending_responses = sum(
            1 for c in contacts if c.relationship_status in ("contacted", "awaiting_response")
        )
        follow_ups_due = sum(
            1 for c in contacts if c.next_follow_up_date and c.next_follow_up_date <= now
        )

        # Build contact responses with recruiter & recent activities
        contact_resps: list[NetworkingContactResponse] = []
        for c in contacts:
            rec_resp = RecruiterProfileResponse.model_validate(c.recruiter) if c.recruiter else None
            recent_acts = c.activities[:5] if c.activities else []
            resp_item = NetworkingContactResponse(
                id=c.id,
                user_id=c.user_id,
                recruiter_id=c.recruiter_id,
                company_id=c.company_id,
                job_id=c.job_id,
                application_id=c.application_id,
                relationship_status=c.relationship_status,
                contact_source=c.contact_source,
                initial_contact_date=c.initial_contact_date,
                last_contact_date=c.last_contact_date,
                next_follow_up_date=c.next_follow_up_date,
                communication_channel=c.communication_channel,
                response_status=c.response_status,
                response_received_at=c.response_received_at,
                networking_notes=c.networking_notes,
                tags=c.tags or [],
                created_at=c.created_at,
                updated_at=c.updated_at,
                recruiter=rec_resp,
                recent_activities=recent_acts,  # type: ignore[arg-type]
            )
            contact_resps.append(resp_item)

        return NetworkingCRMOverviewResponse(
            saved_recruiters_count=saved_count,
            companies_tracked_count=unique_companies,
            outreach_messages_count=outreach_count,
            pending_responses_count=pending_responses,
            follow_ups_due_count=follow_ups_due,
            contacts=contact_resps,
        )

    @classmethod
    def generate_outreach_message(
        cls,
        db: Session,
        user: User,
        data: OutreachGenerateRequest,
    ) -> NetworkingOutreachMessage:
        """Generate personalized outreach message grounded in candidate's actual resume."""
        recruiter = (
            db.query(RecruiterProfile).filter(RecruiterProfile.id == data.recruiter_id).first()
        )
        if not recruiter:
            raise NotFoundError(f"Recruiter with ID {data.recruiter_id} not found.")

        # Ensure contact exists in CRM
        contact = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.user_id == user.id,
                NetworkingContact.recruiter_id == data.recruiter_id,
            )
            .first()
        )
        if not contact:
            contact = cls.get_or_create_contact(
                db=db,
                user=user,
                data=NetworkingContactCreateRequest(
                    recruiter_id=recruiter.id,
                    company_id=recruiter.company_id,
                    job_id=data.job_id,
                    relationship_status="outreach_prepared",
                ),
            )

        # Resolve candidate facts from resume
        job = db.query(Job).filter(Job.id == data.job_id).first() if data.job_id else None
        skills: list[str] = []
        projects: list[str] = []

        resume_id = data.resume_id
        if not resume_id:
            latest_resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if latest_resume:
                resume_id = latest_resume.id

        version: Optional[ResumeVersion] = None
        if resume_id:
            res_obj = (
                db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
            )
            if res_obj and res_obj.current_version_id:
                version = (
                    db.query(ResumeVersion)
                    .filter(ResumeVersion.id == res_obj.current_version_id)
                    .first()
                )
                if version and version.parsed_content:
                    skills = version.parsed_content.get("skills", [])
                    raw_projs = version.parsed_content.get("projects", [])
                    for p in raw_projs:
                        if isinstance(p, dict):
                            projects.append(p.get("title") or p.get("name") or "")
                        elif isinstance(p, str):
                            projects.append(p)

        # Generate outreach draft
        outreach_result = NetworkingOutreachEngine.generate_outreach(
            message_type=data.message_type,
            channel=data.channel,
            tone=data.tone,
            recruiter=recruiter,
            candidate_name=user.full_name,
            candidate_email=user.email,
            job=job,
            skills=skills,
            projects=projects,
            custom_instructions=data.custom_instructions,
            enforce_linkedin_char_limit=data.enforce_linkedin_char_limit,
        )

        message = NetworkingOutreachMessage(
            id=uuid.uuid4(),
            user_id=user.id,
            recruiter_id=recruiter.id,
            relationship_id=contact.id,
            job_id=job.id if job else None,
            resume_version_id=version.id if version else None,
            message_type=data.message_type,
            channel=data.channel,
            tone=data.tone,
            subject=outreach_result.subject,
            body=outreach_result.body,
            grounded_claims=outreach_result.grounded_claims,
            character_count=len(outreach_result.body),
            status="draft",
        )
        db.add(message)

        # Update contact status to outreach_prepared if currently saved or discovered
        if contact.relationship_status in ("discovered", "saved"):
            contact.relationship_status = "outreach_prepared"

        # Log activity
        act = NetworkingActivity(
            id=uuid.uuid4(),
            user_id=user.id,
            recruiter_id=recruiter.id,
            relationship_id=contact.id,
            activity_type="outreach_drafted",
            title=f"Outreach Draft Generated ({data.message_type.replace('_', ' ').title()})",
            description=f"Generated {data.channel.capitalize()} draft for {recruiter.full_name}.",
        )
        db.add(act)

        db.commit()
        db.refresh(message)
        return message

    @classmethod
    def approve_outreach_message(
        cls,
        db: Session,
        user: User,
        message_id: uuid.UUID,
        data: OutreachApproveRequest,
    ) -> NetworkingOutreachMessage:
        message = (
            db.query(NetworkingOutreachMessage)
            .filter(
                NetworkingOutreachMessage.id == message_id,
                NetworkingOutreachMessage.user_id == user.id,
            )
            .first()
        )
        if not message:
            raise NotFoundError(f"Outreach message {message_id} not found.")

        if data.edited_subject is not None:
            message.subject = data.edited_subject.strip()
        message.body = data.edited_body.strip()
        message.character_count = len(message.body)
        message.status = "approved"
        message.approval_confirmed_at = datetime.now(timezone.utc)

        # Log activity
        act = NetworkingActivity(
            id=uuid.uuid4(),
            user_id=user.id,
            recruiter_id=message.recruiter_id,
            relationship_id=message.relationship_id,
            activity_type="outreach_approved",
            title="Outreach Message Approved",
            description="Candidate reviewed and approved outreach message content.",
        )
        db.add(act)

        db.commit()
        db.refresh(message)
        return message

    @classmethod
    def send_outreach_via_gmail(
        cls,
        db: Session,
        user: User,
        message_id: uuid.UUID,
        confirm_send: bool = True,
        attach_resume: bool = True,
    ) -> dict[str, Any]:
        """Dispatch approved networking outreach email via Gmail OAuth."""
        if not confirm_send:
            raise BadRequestError(
                "Explicit confirmation (confirm_send=True) is required to dispatch email."
            )

        message = (
            db.query(NetworkingOutreachMessage)
            .filter(
                NetworkingOutreachMessage.id == message_id,
                NetworkingOutreachMessage.user_id == user.id,
            )
            .first()
        )
        if not message:
            raise NotFoundError(f"Outreach message {message_id} not found.")

        recruiter = (
            db.query(RecruiterProfile).filter(RecruiterProfile.id == message.recruiter_id).first()
        )
        if not recruiter or not recruiter.contact_email:
            raise BadRequestError(
                "Recruiter contact email address is not available or verified. "
                "Nexora strictly forbids guessing recipient email addresses."
            )

        now = datetime.now(timezone.utc)

        # Resolve resume PDF attachment if requested
        attachments: list[dict[str, Any]] = []
        if attach_resume and message.resume_version:
            # Re-use existing compiled PDF path if available
            pdf_path = (
                getattr(message.resume_version, "storage_path", None)
                or message.resume_version.original_filename
            )
            if pdf_path:
                attachments.append(
                    {
                        "filename": f"{user.full_name.replace(' ', '_')}_Resume.pdf",
                        "content_path": pdf_path,
                    }
                )

        try:
            # Execute dispatch through GmailService
            gmail_res = GmailService.send_email(
                db=db,
                user=user,
                recipient_email=recruiter.contact_email,
                subject=message.subject or f"Connecting with {user.full_name}",
                body=message.body,
                confirm_send=confirm_send,
                attachments=None,
            )
            msg_id = (
                gmail_res.get("message_id") if isinstance(gmail_res, dict) else str(uuid.uuid4())
            )

            message.status = "sent"
            message.sent_at = now
            message.sent_via_gmail = True
            message.gmail_message_id = msg_id

            # Update CRM relationship
            contact = message.contact_relationship
            if not contact and message.relationship_id:
                contact = (
                    db.query(NetworkingContact)
                    .filter(NetworkingContact.id == message.relationship_id)
                    .first()
                )
            if contact:
                contact.relationship_status = "contacted"
                contact.communication_channel = "email"
                contact.last_contact_date = now
                contact.next_follow_up_date = now + timedelta(days=5)
                if not contact.initial_contact_date:
                    contact.initial_contact_date = now

                act = NetworkingActivity(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    recruiter_id=recruiter.id,
                    relationship_id=contact.id,
                    activity_type="message_sent",
                    title="Outreach Email Sent via Gmail",
                    description=f"Sent to {recruiter.contact_email}. Next follow-up due in 5 days.",
                )
                db.add(act)

            db.commit()

            audit_service.record_event(
                action="networking_outreach.sent_gmail",
                resource_type="outreach_message",
                resource_id=str(message.id),
                actor_type="user",
                actor_id=str(user.id),
                metadata={"recipient": recruiter.contact_email, "gmail_message_id": msg_id},
            )

            return {
                "status": "success",
                "message": f"Email successfully dispatched to {recruiter.contact_email} via Gmail.",
                "sent_at": now.isoformat(),
                "gmail_message_id": msg_id,
            }
        except Exception as e:
            logger.error("Failed to send outreach email via Gmail: %s", e)
            raise BadRequestError(f"Gmail dispatch failed: {str(e)}") from e

    @classmethod
    def get_follow_up_recommendations(cls, db: Session, user: User) -> FollowUpDueResponse:
        """Analyze networking contacts and surface smart follow-up suggestions."""
        now = datetime.now(timezone.utc)
        contacts = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.user_id == user.id,
                NetworkingContact.relationship_status.in_(
                    ("contacted", "awaiting_response", "follow_up_required")
                ),
            )
            .all()
        )

        items: list[FollowUpDueItem] = []
        for c in contacts:
            rec = c.recruiter
            if not rec:
                continue

            days = 0
            if c.last_contact_date:
                days = (now - c.last_contact_date).days

            is_due = (c.next_follow_up_date and c.next_follow_up_date <= now) or days >= 5

            if is_due:
                reason = (
                    f"Outreach sent {days} days ago with no response recorded."
                    if days >= 5
                    else "Scheduled follow-up date has arrived."
                )
                items.append(
                    FollowUpDueItem(
                        relationship_id=c.id,
                        recruiter_id=rec.id,
                        recruiter_name=rec.full_name,
                        company_name=rec.company_name,
                        communication_channel=c.communication_channel,
                        relationship_status=c.relationship_status,
                        days_since_last_contact=days,
                        reason=reason,
                        recommended_action="Send courteous follow-up inquiry",
                        suggested_message_type="follow_up",
                    )
                )

        return FollowUpDueResponse(
            total_due=len(items),
            items=items,
        )

    @classmethod
    def delete_contact(cls, db: Session, user: User, relationship_id: uuid.UUID) -> dict[str, str]:
        contact = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.id == relationship_id,
                NetworkingContact.user_id == user.id,
            )
            .first()
        )
        if not contact:
            raise NotFoundError(f"Networking contact {relationship_id} not found.")

        db.delete(contact)
        db.commit()
        return {"status": "success", "message": "Contact removed from CRM."}
