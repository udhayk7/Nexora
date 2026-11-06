import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.models.application import (
    ApplicationActivity,
    ApplicationInterview,
    ApplicationStatusHistory,
    JobApplication,
)
from app.models.company import Company
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.schemas.application import (
    ApplicationActivityCreate,
    ApplicationActivityResponse,
    ApplicationActivityUpdate,
    ApplicationAnalyticsResponse,
    ApplicationInterviewCreate,
    ApplicationInterviewResponse,
    ApplicationInterviewUpdate,
    ApplicationStatusHistoryResponse,
    JobApplicationCreate,
    JobApplicationDetailResponse,
    JobApplicationListResponse,
    JobApplicationStatusUpdate,
    JobApplicationSummaryResponse,
    JobApplicationUpdate,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ApplicationService:
    """
    Service managing job applications, status transitions, activity timeline events,
    interviews, and real database analytics.
    """

    @classmethod
    def create_application(
        cls,
        db: Session,
        user_id: uuid.UUID,
        data: JobApplicationCreate,
    ) -> JobApplicationDetailResponse:
        """Create a new tracked job application for the authenticated user."""
        company_name = data.company_name.strip()
        company_id = data.company_id
        job_id = data.job_id

        # 1. Validate Job if linked
        if job_id:
            job = db.get(Job, job_id)
            if not job:
                raise NotFoundError(f"Job opportunity {job_id} not found.")
            if not company_id and job.company_id:
                company_id = job.company_id
            if not company_name and job.company:
                company_name = job.company.name

        # 2. Validate Company if linked
        if company_id:
            company = db.get(Company, company_id)
            if not company:
                raise NotFoundError(f"Company {company_id} not found.")
            if not company_name:
                company_name = company.name

        if not company_name:
            raise BadRequestError("Company name is required.")

        # 3. Validate Resume and Version ownership
        if data.resume_id:
            resume = db.get(Resume, data.resume_id)
            if not resume or resume.user_id != user_id:
                raise NotFoundError(f"Resume {data.resume_id} not found.")

        if data.resume_version_id:
            version = db.get(ResumeVersion, data.resume_version_id)
            if not version or (data.resume_id and version.resume_id != data.resume_id):
                raise NotFoundError(f"Resume version {data.resume_version_id} not found.")

        applied_at = data.applied_at
        if data.status == "applied" and not applied_at:
            applied_at = datetime.now(timezone.utc)

        # 4. Instantiate Application
        application = JobApplication(
            id=uuid.uuid4(),
            user_id=user_id,
            job_id=job_id,
            company_id=company_id,
            title=data.title.strip(),
            company_name=company_name,
            status=data.status,
            application_channel=data.application_channel,
            application_url=data.application_url,
            applied_at=applied_at,
            resume_id=data.resume_id,
            resume_version_id=data.resume_version_id,
            recruiter_name=data.recruiter_name,
            recruiter_email=data.recruiter_email,
            recruiter_phone=data.recruiter_phone,
            deadline_at=data.deadline_at,
            next_follow_up_at=data.next_follow_up_at,
            notes=data.notes,
            submission_confirmed=data.submission_confirmed,
            metadata_json=data.metadata_json or {},
        )
        db.add(application)
        db.flush()

        # 5. Record Initial Status History
        history = ApplicationStatusHistory(
            id=uuid.uuid4(),
            application_id=application.id,
            from_status=None,
            to_status=data.status,
            notes="Application tracking record created.",
            changed_at=datetime.now(timezone.utc),
        )
        db.add(history)

        # 6. Record Initial Activity
        act_title = (
            "Application Submitted"
            if data.status == "applied"
            else f"Tracking Started ({data.status.capitalize()})"
        )
        act_type = "application_submitted" if data.status == "applied" else "status_changed"
        activity = ApplicationActivity(
            id=uuid.uuid4(),
            application_id=application.id,
            user_id=user_id,
            activity_type=act_type,
            title=act_title,
            description=f"Created application for {application.title} at {company_name}.",
            activity_date=datetime.now(timezone.utc),
            metadata_json={},
        )
        db.add(activity)

        db.commit()
        db.refresh(application)

        audit_service.record_event(
            action="application.created",
            resource_type="job_application",
            resource_id=str(application.id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={
                "title": application.title,
                "company_name": company_name,
                "status": application.status,
                "channel": application.application_channel,
            },
        )

        return cls.get_application_detail(db, user_id, application.id)

    @classmethod
    def list_applications(
        cls,
        db: Session,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at_desc",
        page: int = 1,
        per_page: int = 20,
    ) -> JobApplicationListResponse:
        """List and filter job applications with counts and pagination."""
        stmt = select(JobApplication).where(JobApplication.user_id == user_id)

        if status and status != "all":
            stmt = stmt.where(JobApplication.status == status)

        if channel and channel != "all":
            stmt = stmt.where(JobApplication.application_channel == channel)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    JobApplication.title.ilike(term),
                    JobApplication.company_name.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sorting
        if sort_by == "created_at_asc":
            stmt = stmt.order_by(JobApplication.created_at.asc())
        elif sort_by == "applied_at_desc":
            stmt = stmt.order_by(JobApplication.applied_at.desc().nullslast())
        elif sort_by == "deadline_asc":
            stmt = stmt.order_by(JobApplication.deadline_at.asc().nullslast())
        elif sort_by == "next_follow_up_asc":
            stmt = stmt.order_by(JobApplication.next_follow_up_at.asc().nullslast())
        elif sort_by == "company_asc":
            stmt = stmt.order_by(JobApplication.company_name.asc())
        elif sort_by == "title_asc":
            stmt = stmt.order_by(JobApplication.title.asc())
        else:
            stmt = stmt.order_by(JobApplication.created_at.desc())

        # Pagination
        offset = (page - 1) * per_page
        stmt = (
            stmt.offset(offset)
            .limit(per_page)
            .options(
                selectinload(JobApplication.interviews),
                selectinload(JobApplication.activities),
            )
        )
        apps = db.scalars(stmt).all()

        items: list[JobApplicationSummaryResponse] = []
        for a in apps:
            items.append(
                JobApplicationSummaryResponse(
                    id=a.id,
                    user_id=a.user_id,
                    job_id=a.job_id,
                    company_id=a.company_id,
                    title=a.title,
                    company_name=a.company_name,
                    status=a.status,
                    application_channel=a.application_channel,
                    applied_at=a.applied_at,
                    deadline_at=a.deadline_at,
                    next_follow_up_at=a.next_follow_up_at,
                    submission_confirmed=a.submission_confirmed,
                    interviews_count=len(a.interviews),
                    activities_count=len(a.activities),
                    created_at=a.created_at,
                    updated_at=a.updated_at,
                )
            )

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        return JobApplicationListResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    @classmethod
    def get_application_detail(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> JobApplicationDetailResponse:
        """Fetch full application detail including timeline, status history, and interviews."""
        stmt = (
            select(JobApplication)
            .where(
                JobApplication.id == application_id,
                JobApplication.user_id == user_id,
            )
            .options(
                selectinload(JobApplication.status_history),
                selectinload(JobApplication.activities),
                selectinload(JobApplication.interviews),
                selectinload(JobApplication.resume),
                selectinload(JobApplication.resume_version),
            )
        )
        app = db.scalars(stmt).first()
        if not app:
            raise NotFoundError(f"Job application {application_id} not found.")

        history_items = [
            ApplicationStatusHistoryResponse.model_validate(h) for h in app.status_history
        ]
        activity_items = [ApplicationActivityResponse.model_validate(act) for act in app.activities]
        interview_items = [ApplicationInterviewResponse.model_validate(iv) for iv in app.interviews]

        resume_title = app.resume.title if app.resume else None
        version_num = app.resume_version.version_number if app.resume_version else None

        return JobApplicationDetailResponse(
            id=app.id,
            user_id=app.user_id,
            job_id=app.job_id,
            company_id=app.company_id,
            title=app.title,
            company_name=app.company_name,
            status=app.status,
            application_channel=app.application_channel,
            application_url=app.application_url,
            applied_at=app.applied_at,
            resume_id=app.resume_id,
            resume_version_id=app.resume_version_id,
            resume_title=resume_title,
            resume_version_number=version_num,
            recruiter_name=app.recruiter_name,
            recruiter_email=app.recruiter_email,
            recruiter_phone=app.recruiter_phone,
            deadline_at=app.deadline_at,
            next_follow_up_at=app.next_follow_up_at,
            notes=app.notes,
            submission_confirmed=app.submission_confirmed,
            link_opened_at=app.link_opened_at,
            metadata_json=app.metadata_json or {},
            interviews_count=len(app.interviews),
            activities_count=len(app.activities),
            created_at=app.created_at,
            updated_at=app.updated_at,
            status_history=history_items,
            activities=activity_items,
            interviews=interview_items,
        )

    @classmethod
    def update_application(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: JobApplicationUpdate,
    ) -> JobApplicationDetailResponse:
        """Update editable fields of an existing application."""
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        if data.resume_id is not None:
            if data.resume_id:
                resume = db.get(Resume, data.resume_id)
                if not resume or resume.user_id != user_id:
                    raise NotFoundError(f"Resume {data.resume_id} not found.")
            app.resume_id = data.resume_id

        if data.resume_version_id is not None:
            if data.resume_version_id:
                version = db.get(ResumeVersion, data.resume_version_id)
                if not version or (app.resume_id and version.resume_id != app.resume_id):
                    raise NotFoundError(f"Resume version {data.resume_version_id} not found.")
            app.resume_version_id = data.resume_version_id

        if data.title is not None:
            app.title = data.title.strip()
        if data.company_name is not None:
            app.company_name = data.company_name.strip()
        if data.company_id is not None:
            app.company_id = data.company_id
        if data.job_id is not None:
            app.job_id = data.job_id
        if data.application_channel is not None:
            app.application_channel = data.application_channel
        if data.application_url is not None:
            app.application_url = data.application_url
        if data.applied_at is not None:
            app.applied_at = data.applied_at
        if data.recruiter_name is not None:
            app.recruiter_name = data.recruiter_name
        if data.recruiter_email is not None:
            app.recruiter_email = data.recruiter_email
        if data.recruiter_phone is not None:
            app.recruiter_phone = data.recruiter_phone
        if data.deadline_at is not None:
            app.deadline_at = data.deadline_at
        if data.next_follow_up_at is not None:
            app.next_follow_up_at = data.next_follow_up_at
        if data.submission_confirmed is not None:
            app.submission_confirmed = data.submission_confirmed
        if data.metadata_json is not None:
            app.metadata_json = data.metadata_json

        # If notes changed, log a personal note activity
        if data.notes is not None and data.notes != app.notes:
            app.notes = data.notes
            activity = ApplicationActivity(
                id=uuid.uuid4(),
                application_id=app.id,
                user_id=user_id,
                activity_type="personal_note",
                title="Notes Updated",
                description="Personal application notes were modified.",
                activity_date=datetime.now(timezone.utc),
                metadata_json={},
            )
            db.add(activity)

        db.commit()

        audit_service.record_event(
            action="application.updated",
            resource_type="job_application",
            resource_id=str(application_id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"title": app.title},
        )

        return cls.get_application_detail(db, user_id, application_id)

    @classmethod
    def update_status(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: JobApplicationStatusUpdate,
    ) -> JobApplicationDetailResponse:
        """Update application status, maintaining complete historical timeline."""
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        old_status = app.status
        new_status = data.status

        if old_status != new_status:
            app.status = new_status

            if new_status == "applied":
                if data.applied_at:
                    app.applied_at = data.applied_at
                elif not app.applied_at:
                    app.applied_at = datetime.now(timezone.utc)
                if data.submission_confirmed is not None:
                    app.submission_confirmed = data.submission_confirmed
                else:
                    app.submission_confirmed = True

            elif data.submission_confirmed is not None:
                app.submission_confirmed = data.submission_confirmed

            # Record Status History
            history = ApplicationStatusHistory(
                id=uuid.uuid4(),
                application_id=app.id,
                from_status=old_status,
                to_status=new_status,
                notes=data.notes,
                changed_at=datetime.now(timezone.utc),
            )
            db.add(history)

            # Record Activity
            if new_status == "applied":
                act_type = "application_submitted"
                act_title = "Application Submitted"
                act_desc = data.notes or f"Application submitted for {app.title}."
            elif new_status == "offer":
                act_type = "offer_received"
                act_title = "Offer Received"
                act_desc = data.notes or f"Job offer received for {app.title}."
            else:
                act_type = "status_changed"
                act_title = f"Status: {new_status.capitalize()}"
                act_desc = data.notes or (
                    f"Status changed from {old_status.capitalize()} to {new_status.capitalize()}."
                )

            activity = ApplicationActivity(
                id=uuid.uuid4(),
                application_id=app.id,
                user_id=user_id,
                activity_type=act_type,
                title=act_title,
                description=act_desc,
                activity_date=datetime.now(timezone.utc),
                metadata_json={"from_status": old_status, "to_status": new_status},
            )
            db.add(activity)

            db.commit()

            audit_service.record_event(
                action="application.status_changed",
                resource_type="job_application",
                resource_id=str(application_id),
                actor_type="user",
                actor_id=str(user_id),
                metadata={
                    "from_status": old_status,
                    "to_status": new_status,
                    "submission_confirmed": app.submission_confirmed,
                },
            )

        return cls.get_application_detail(db, user_id, application_id)

    @classmethod
    def record_link_opened(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> JobApplicationDetailResponse:
        """
        Record that user viewed or opened the external application link.
        Does NOT automatically change status to 'applied' or claim submission.
        """
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        now = datetime.now(timezone.utc)
        app.link_opened_at = now

        activity = ApplicationActivity(
            id=uuid.uuid4(),
            application_id=app.id,
            user_id=user_id,
            activity_type="other",
            title="Application Portal Opened",
            description="User accessed external application link. Submission unconfirmed.",
            activity_date=now,
            metadata_json={},
        )
        db.add(activity)
        db.commit()

        audit_service.record_event(
            action="application.link_opened",
            resource_type="job_application",
            resource_id=str(application_id),
            actor_type="user",
            actor_id=str(user_id),
        )

        return cls.get_application_detail(db, user_id, application_id)

    @classmethod
    def delete_application(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> None:
        """Delete an application and its timeline without affecting shared entities."""
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        title = app.title
        db.delete(app)
        db.commit()

        audit_service.record_event(
            action="application.deleted",
            resource_type="job_application",
            resource_id=str(application_id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"title": title},
        )

    # --- Activities CRUD ---

    @classmethod
    def add_activity(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: ApplicationActivityCreate,
    ) -> ApplicationActivityResponse:
        """Add custom activity or personal note to an application."""
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        activity = ApplicationActivity(
            id=uuid.uuid4(),
            application_id=app.id,
            user_id=user_id,
            activity_type=data.activity_type,
            title=data.title.strip(),
            description=data.description,
            activity_date=data.activity_date or datetime.now(timezone.utc),
            metadata_json=data.metadata_json or {},
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)

        audit_service.record_event(
            action="application.activity_added",
            resource_type="application_activity",
            resource_id=str(activity.id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"activity_type": activity.activity_type},
        )

        return ApplicationActivityResponse.model_validate(activity)

    @classmethod
    def update_activity(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        activity_id: uuid.UUID,
        data: ApplicationActivityUpdate,
    ) -> ApplicationActivityResponse:
        """Update an existing activity or note."""
        act = db.get(ApplicationActivity, activity_id)
        if not act or act.application_id != application_id or act.user_id != user_id:
            raise NotFoundError(f"Activity {activity_id} not found.")

        if data.title is not None:
            act.title = data.title.strip()
        if data.description is not None:
            act.description = data.description
        if data.activity_date is not None:
            act.activity_date = data.activity_date
        if data.metadata_json is not None:
            act.metadata_json = data.metadata_json

        db.commit()
        db.refresh(act)
        return ApplicationActivityResponse.model_validate(act)

    @classmethod
    def delete_activity(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        activity_id: uuid.UUID,
    ) -> None:
        """Delete an activity or note."""
        act = db.get(ApplicationActivity, activity_id)
        if not act or act.application_id != application_id or act.user_id != user_id:
            raise NotFoundError(f"Activity {activity_id} not found.")

        db.delete(act)
        db.commit()

        audit_service.record_event(
            action="application.activity_deleted",
            resource_type="application_activity",
            resource_id=str(activity_id),
            actor_type="user",
            actor_id=str(user_id),
        )

    # --- Interviews & Assessments CRUD ---

    @classmethod
    def create_interview(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: ApplicationInterviewCreate,
    ) -> ApplicationInterviewResponse:
        """Schedule or record an interview / assessment round."""
        app = db.get(JobApplication, application_id)
        if not app or app.user_id != user_id:
            raise NotFoundError(f"Job application {application_id} not found.")

        interview = ApplicationInterview(
            id=uuid.uuid4(),
            application_id=app.id,
            user_id=user_id,
            interview_type=data.interview_type,
            title=data.title.strip(),
            round_number=data.round_number,
            scheduled_at=data.scheduled_at,
            duration_minutes=data.duration_minutes,
            meeting_url=data.meeting_url,
            interviewer_names=data.interviewer_names,
            preparation_notes=data.preparation_notes,
            feedback=data.feedback,
            status=data.status,
            outcome=data.outcome,
            next_steps=data.next_steps,
        )
        db.add(interview)

        # Log timeline activity
        is_assessment = "assessment" in data.interview_type
        act_type = "assessment_scheduled" if is_assessment else "interview_scheduled"
        act_title = (
            f"Assessment Scheduled: {interview.title}"
            if is_assessment
            else f"Interview Scheduled: Round {interview.round_number} ({interview.title})"
        )
        activity = ApplicationActivity(
            id=uuid.uuid4(),
            application_id=app.id,
            user_id=user_id,
            activity_type=act_type,
            title=act_title,
            description=f"Scheduled for {data.scheduled_at.strftime('%b %d, %Y %H:%M UTC')}.",
            activity_date=data.scheduled_at,
            metadata_json={"interview_id": str(interview.id)},
        )
        db.add(activity)

        db.commit()
        db.refresh(interview)

        audit_service.record_event(
            action="application.interview_created",
            resource_type="application_interview",
            resource_id=str(interview.id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"type": interview.interview_type, "round": interview.round_number},
        )

        return ApplicationInterviewResponse.model_validate(interview)

    @classmethod
    def update_interview(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        interview_id: uuid.UUID,
        data: ApplicationInterviewUpdate,
    ) -> ApplicationInterviewResponse:
        """Update interview details, outcome, feedback, or status."""
        iv = db.get(ApplicationInterview, interview_id)
        if not iv or iv.application_id != application_id or iv.user_id != user_id:
            raise NotFoundError(f"Interview {interview_id} not found.")

        old_status = iv.status

        if data.interview_type is not None:
            iv.interview_type = data.interview_type
        if data.title is not None:
            iv.title = data.title.strip()
        if data.round_number is not None:
            iv.round_number = data.round_number
        if data.scheduled_at is not None:
            iv.scheduled_at = data.scheduled_at
        if data.duration_minutes is not None:
            iv.duration_minutes = data.duration_minutes
        if data.meeting_url is not None:
            iv.meeting_url = data.meeting_url
        if data.interviewer_names is not None:
            iv.interviewer_names = data.interviewer_names
        if data.preparation_notes is not None:
            iv.preparation_notes = data.preparation_notes
        if data.feedback is not None:
            iv.feedback = data.feedback
        if data.status is not None:
            iv.status = data.status
        if data.outcome is not None:
            iv.outcome = data.outcome
        if data.next_steps is not None:
            iv.next_steps = data.next_steps

        # If completed, add activity
        if iv.status == "completed" and old_status != "completed":
            is_assessment = "assessment" in iv.interview_type
            act_type = "assessment_completed" if is_assessment else "interview_completed"
            act_title = (
                f"Assessment Completed: {iv.title}"
                if is_assessment
                else f"Interview Completed: Round {iv.round_number} ({iv.title})"
            )
            activity = ApplicationActivity(
                id=uuid.uuid4(),
                application_id=application_id,
                user_id=user_id,
                activity_type=act_type,
                title=act_title,
                description=iv.feedback or f"Outcome: {iv.outcome.capitalize()}.",
                activity_date=datetime.now(timezone.utc),
                metadata_json={"outcome": iv.outcome},
            )
            db.add(activity)

        db.commit()
        db.refresh(iv)

        audit_service.record_event(
            action="application.interview_updated",
            resource_type="application_interview",
            resource_id=str(interview_id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"status": iv.status, "outcome": iv.outcome},
        )

        return ApplicationInterviewResponse.model_validate(iv)

    @classmethod
    def delete_interview(
        cls,
        db: Session,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        interview_id: uuid.UUID,
    ) -> None:
        """Delete an interview / assessment record."""
        iv = db.get(ApplicationInterview, interview_id)
        if not iv or iv.application_id != application_id or iv.user_id != user_id:
            raise NotFoundError(f"Interview {interview_id} not found.")

        db.delete(iv)
        db.commit()

        audit_service.record_event(
            action="application.interview_deleted",
            resource_type="application_interview",
            resource_id=str(interview_id),
            actor_type="user",
            actor_id=str(user_id),
        )

    # --- Real Database Analytics ---

    @classmethod
    def get_analytics(cls, db: Session, user_id: uuid.UUID) -> ApplicationAnalyticsResponse:
        """
        Compute dashboard metrics, pipelines, and upcoming events strictly
        from real database records.
        """
        now = datetime.now(timezone.utc)
        two_weeks_out = now + timedelta(days=14)

        # 1. Fetch user's applications
        apps = (
            db.query(JobApplication)
            .filter(JobApplication.user_id == user_id)
            .order_by(JobApplication.created_at.desc())
            .all()
        )
        total_applications = len(apps)

        status_dist: dict[str, int] = {
            "interested": 0,
            "preparing": 0,
            "applied": 0,
            "shortlisted": 0,
            "assessment": 0,
            "interview": 0,
            "offer": 0,
            "rejected": 0,
            "withdrawn": 0,
        }
        channel_dist: dict[str, int] = {
            "official_portal": 0,
            "email": 0,
            "referral": 0,
            "external_form": 0,
            "other": 0,
        }

        in_progress_statuses = {
            "interested",
            "preparing",
            "applied",
            "shortlisted",
            "assessment",
            "interview",
        }
        in_progress_count = 0
        offers_count = 0
        rejections_count = 0
        upcoming_deadlines_count = 0
        upcoming_follow_ups_count = 0

        upcoming_events: list[dict[str, Any]] = []

        for a in apps:
            if a.status in status_dist:
                status_dist[a.status] += 1
            if a.application_channel in channel_dist:
                channel_dist[a.application_channel] += 1

            if a.status in in_progress_statuses:
                in_progress_count += 1
            elif a.status == "offer":
                offers_count += 1
            elif a.status == "rejected":
                rejections_count += 1

            # Deadlines within 14 days
            deadline = _ensure_utc(a.deadline_at)
            if deadline and now <= deadline <= two_weeks_out:
                upcoming_deadlines_count += 1
                upcoming_events.append(
                    {
                        "type": "deadline",
                        "title": f"Deadline: {a.title} ({a.company_name})",
                        "date": deadline.isoformat(),
                        "application_id": str(a.id),
                    }
                )

            # Follow-ups within 14 days
            follow_up = _ensure_utc(a.next_follow_up_at)
            if follow_up and now <= follow_up <= two_weeks_out:
                upcoming_follow_ups_count += 1
                upcoming_events.append(
                    {
                        "type": "follow_up",
                        "title": f"Follow-up: {a.company_name} - {a.title}",
                        "date": follow_up.isoformat(),
                        "application_id": str(a.id),
                    }
                )

        # 2. Interviews & Assessments
        raw_interviews = (
            db.query(ApplicationInterview)
            .filter(
                ApplicationInterview.user_id == user_id,
                ApplicationInterview.status == "scheduled",
            )
            .all()
        )
        interviews = [
            iv
            for iv in raw_interviews
            if iv.scheduled_at and _ensure_utc(iv.scheduled_at) >= now  # type: ignore[operator]
        ]
        interviews.sort(key=lambda iv: _ensure_utc(iv.scheduled_at) or now)

        interviews_scheduled_count = sum(
            1 for iv in interviews if "assessment" not in iv.interview_type
        )
        assessments_pending_count = sum(1 for iv in interviews if "assessment" in iv.interview_type)

        for iv in interviews:
            is_assessment = "assessment" in iv.interview_type
            upcoming_events.append(
                {
                    "type": "assessment" if is_assessment else "interview",
                    "title": iv.title,
                    "date": iv.scheduled_at.isoformat(),
                    "application_id": str(iv.application_id),
                    "meeting_url": iv.meeting_url,
                }
            )

        # Sort upcoming events chronologically
        upcoming_events.sort(key=lambda ev: ev["date"])

        # 3. Simple activity trend (count created in the past 6 weeks)
        activity_trend: list[dict[str, Any]] = []
        for week_idx in range(5, -1, -1):
            start_w = now - timedelta(days=(week_idx + 1) * 7)
            end_w = now - timedelta(days=week_idx * 7)
            count = len(
                [
                    a
                    for a in apps
                    if a.created_at and start_w <= _ensure_utc(a.created_at) < end_w  # type: ignore[operator]
                ]
            )
            label = start_w.strftime("%b %d")
            activity_trend.append({"week": label, "count": count})

        return ApplicationAnalyticsResponse(
            total_applications=total_applications,
            in_progress_count=in_progress_count,
            interviews_scheduled_count=interviews_scheduled_count,
            assessments_pending_count=assessments_pending_count,
            offers_count=offers_count,
            rejections_count=rejections_count,
            upcoming_deadlines_count=upcoming_deadlines_count,
            upcoming_follow_ups_count=upcoming_follow_ups_count,
            status_distribution=status_dist,
            channel_distribution=channel_dist,
            activity_trend=activity_trend,
            upcoming_events=upcoming_events,
        )
