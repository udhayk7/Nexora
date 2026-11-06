import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.config import settings
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.models.analysis import ResumeAnalysis
from app.models.job import Job
from app.models.match import JobMatch, UserMatchingPreference
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.match import (
    GapSignal,
    JobMatchListResponse,
    JobMatchResponse,
    JobMatchRunRequest,
    JobMatchRunResult,
    JobMatchStateUpdate,
    PositiveSignal,
    ScoreBreakdown,
    UserMatchingPreferenceResponse,
    UserMatchingPreferenceUpdate,
)
from app.services.job_service import JobService, compute_job_freshness
from app.services.matching_engine import ENGINE_VERSION, MatchingEngine


class MatchingService:
    """Orchestrates job matching preferences, execution, ranking, and state management."""

    # -------------------------------------------------------------------------
    # Preferences Management
    # -------------------------------------------------------------------------
    @classmethod
    def get_user_preferences(
        cls,
        db: Session,
        user: User,
    ) -> UserMatchingPreferenceResponse:
        """Fetch matching preferences for the current user; initializes defaults if unset."""
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not pref:
            pref = UserMatchingPreference(
                user_id=user.id,
                target_role_families=[],
                preferred_locations=[],
                work_arrangement_preferences=[],
                min_salary=None,
                salary_currency="INR",
                salary_period="annual",
                seniority_preferences=[],
                preferred_industries=[],
                excluded_industries=[],
                preferred_skills=[],
                excluded_terms=[],
                excluded_roles=[],
                preferred_company_sizes=[],
                metadata_json={},
                is_active=True,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)

        return UserMatchingPreferenceResponse.model_validate(pref)

    @classmethod
    def update_user_preferences(
        cls,
        db: Session,
        user: User,
        data: UserMatchingPreferenceUpdate,
    ) -> UserMatchingPreferenceResponse:
        """Update candidate matching preferences with validation."""
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not pref:
            pref = UserMatchingPreference(user_id=user.id)
            db.add(pref)

        update_dict = data.model_dump()
        for k, v in update_dict.items():
            setattr(pref, k, v)

        db.commit()
        db.refresh(pref)

        audit_service.record_event(
            action="match.preferences_updated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="matching_preference",
            resource_id=str(pref.id),
            metadata={
                "target_roles_count": len(pref.target_role_families),
                "has_min_salary": pref.min_salary is not None,
                "preferred_arrangements": pref.work_arrangement_preferences,
            },
        )

        return UserMatchingPreferenceResponse.model_validate(pref)

    # -------------------------------------------------------------------------
    # Match Execution & Recomputation
    # -------------------------------------------------------------------------
    @classmethod
    def run_matching(
        cls,
        db: Session,
        user: User,
        request: JobMatchRunRequest,
    ) -> JobMatchRunResult:
        """Execute deterministic job matching for user's analyzed resume version."""
        # 1. Resolve Resume and Version
        resume_id = request.resume_id
        version_id = request.version_id

        if not resume_id:
            latest_resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if not latest_resume:
                raise BadRequestError(
                    "No resume found. Upload and parse a resume in Resume Studio first."
                )
            resume_id = latest_resume.id
            if not version_id:
                version_id = latest_resume.current_version_id
        else:
            resume = (
                db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
            )
            if not resume:
                raise NotFoundError("Specified resume not found or does not belong to you.")
            if not version_id:
                version_id = resume.current_version_id

        if not version_id:
            version = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.resume_id == resume_id)
                .order_by(ResumeVersion.version_number.desc())
                .first()
            )
            if not version:
                raise BadRequestError("No version found for the selected resume.")
            version_id = version.id

        # 2. Resolve Resume Analysis
        analysis = (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.user_id == user.id,
                ResumeAnalysis.version_id == version_id,
                ResumeAnalysis.status == "completed",
            )
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
        if not analysis or not analysis.result:
            raise BadRequestError(
                "Selected resume version has not been analyzed yet. "
                "Run AI Resume Intelligence in Resume Studio first."
            )

        resume_analysis_result = ResumeAnalysisResult.model_validate(analysis.result)

        # 3. Load User Preferences (if any)
        preferences = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )

        # 4. Fetch Active Job Requisitions
        limit = request.limit or 100
        jobs = (
            db.query(Job)
            .filter(Job.job_status != "closed")
            .order_by(Job.first_seen_at.desc())
            .limit(limit)
            .all()
        )

        computed_count = 0
        saved_count = 0
        min_threshold = request.min_score_threshold or 0.0

        for job in jobs:
            freshness = compute_job_freshness(job.last_verified_at or job.first_seen_at)
            job.freshness = freshness  # type: ignore[attr-defined]
            score, breakdown, positives, gaps = MatchingEngine.evaluate_match(
                job=job,
                resume_analysis=resume_analysis_result,
                preferences=preferences,
            )
            computed_count += 1

            if score < min_threshold:
                continue

            # Upsert into job_matches
            existing_match = (
                db.query(JobMatch)
                .filter(
                    JobMatch.user_id == user.id,
                    JobMatch.job_id == job.id,
                    JobMatch.version_id == version_id,
                    JobMatch.engine_version == ENGINE_VERSION,
                )
                .first()
            )

            positive_payload = [p.model_dump() for p in positives]
            gap_payload = [g.model_dump() for g in gaps]
            breakdown_payload = breakdown.model_dump()

            if existing_match:
                existing_match.match_score = score
                existing_match.score_breakdown = breakdown_payload
                existing_match.positive_signals = positive_payload
                existing_match.gap_signals = gap_payload
                existing_match.analysis_id = analysis.id
                existing_match.resume_id = resume_id
            else:
                new_match = JobMatch(
                    user_id=user.id,
                    job_id=job.id,
                    resume_id=resume_id,
                    version_id=version_id,
                    analysis_id=analysis.id,
                    engine_version=ENGINE_VERSION,
                    match_score=score,
                    score_breakdown=breakdown_payload,
                    positive_signals=positive_payload,
                    gap_signals=gap_payload,
                    is_saved=False,
                    is_dismissed=False,
                )
                db.add(new_match)

            saved_count += 1

        db.commit()

        audit_service.record_event(
            action="match.generated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job_match",
            resource_id=str(resume_id),
            metadata={
                "matches_computed": computed_count,
                "matches_saved": saved_count,
                "version_id": str(version_id),
                "engine_version": ENGINE_VERSION,
            },
        )

        return JobMatchRunResult(
            matches_computed=computed_count,
            matches_saved=saved_count,
            resume_id=resume_id,
            version_id=version_id,
            analysis_id=analysis.id,
            engine_version=ENGINE_VERSION,
            message=f"Matching completed: {saved_count} opportunities ranked and saved.",
        )

    @classmethod
    def recompute_matches(
        cls,
        db: Session,
        user: User,
    ) -> JobMatchRunResult:
        """Recompute match scores using latest preferences and analyzed resume."""
        res = cls.run_matching(db=db, user=user, request=JobMatchRunRequest())
        audit_service.record_event(
            action="match.recomputed",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job_match",
            resource_id=str(user.id),
            metadata={"matches_saved": res.matches_saved},
        )
        return res

    # -------------------------------------------------------------------------
    # List & Retrieve Matches
    # -------------------------------------------------------------------------
    @classmethod
    def _format_match_response(cls, match: JobMatch) -> JobMatchResponse:
        """Map SQLAlchemy JobMatch entity to Pydantic JobMatchResponse schema."""
        job_resp = JobService._format_job_response(match.job) if match.job else None
        breakdown = ScoreBreakdown.model_validate(match.score_breakdown)
        positives = [PositiveSignal.model_validate(p) for p in (match.positive_signals or [])]
        gaps = [GapSignal.model_validate(g) for g in (match.gap_signals or [])]

        return JobMatchResponse(
            id=match.id,
            user_id=match.user_id,
            job_id=match.job_id,
            resume_id=match.resume_id,
            version_id=match.version_id,
            analysis_id=match.analysis_id,
            engine_version=match.engine_version,
            match_score=match.match_score,
            score_breakdown=breakdown,
            positive_signals=positives,
            gap_signals=gaps,
            is_saved=match.is_saved,
            is_dismissed=match.is_dismissed,
            created_at=match.created_at,
            updated_at=match.updated_at,
            job=job_resp,
        )

    @classmethod
    def list_matches(
        cls,
        db: Session,
        user: User,
        role_family: Optional[str] = None,
        location: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        freshness: Optional[str] = None,
        verification_status: Optional[str] = None,
        min_score: Optional[float] = None,
        is_saved: Optional[bool] = None,
        include_dismissed: bool = False,
        sort_by: str = "score",
        page: int = 1,
        per_page: int = 20,
    ) -> JobMatchListResponse:
        """Retrieve paginated and ranked career matches for the authenticated user."""
        query = db.query(JobMatch).join(JobMatch.job).filter(JobMatch.user_id == user.id)

        if not include_dismissed:
            query = query.filter(JobMatch.is_dismissed.is_(False))

        if is_saved is not None:
            query = query.filter(JobMatch.is_saved.is_(is_saved))

        if min_score is not None:
            query = query.filter(JobMatch.match_score >= min_score)

        if role_family and role_family != "all":
            query = query.filter(Job.role_family == role_family)

        if work_arrangement and work_arrangement != "all":
            query = query.filter(Job.work_arrangement == work_arrangement)

        if verification_status and verification_status != "all":
            query = query.filter(Job.verification_status == verification_status)

        if freshness and freshness != "all":
            now = datetime.now(timezone.utc)
            cutoff_recent = now - timedelta(days=settings.JOB_FRESHNESS_RECENT_DAYS)
            cutoff_due = now - timedelta(days=settings.JOB_FRESHNESS_DUE_DAYS)
            if freshness == "recent":
                query = query.filter(Job.last_checked_at >= cutoff_recent)
            elif freshness == "due_for_review":
                query = query.filter(
                    Job.last_checked_at < cutoff_recent,
                    Job.last_checked_at >= cutoff_due,
                )
            elif freshness == "stale":
                query = query.filter(Job.last_checked_at < cutoff_due)
            elif freshness == "unknown":
                query = query.filter(Job.last_checked_at.is_(None))

        if location and location.strip():
            loc_term = f"%{location.strip()}%"
            query = query.filter(
                (Job.city.ilike(loc_term))
                | (Job.country.ilike(loc_term))
                | (Job.location_text.ilike(loc_term))
            )

        total = query.count()
        safe_per_page = max(1, min(per_page, 100))
        total_pages = math.ceil(total / safe_per_page) if total > 0 else 1
        safe_page = max(1, min(page, max(1, total_pages)))

        if sort_by == "date":
            query = query.order_by(JobMatch.created_at.desc())
        else:
            query = query.order_by(JobMatch.match_score.desc(), JobMatch.created_at.desc())

        records = query.offset((safe_page - 1) * safe_per_page).limit(safe_per_page).all()
        items = [cls._format_match_response(m) for m in records]

        return JobMatchListResponse(
            items=items,
            total=total,
            page=safe_page,
            per_page=safe_per_page,
            total_pages=total_pages,
        )

    @classmethod
    def get_match_detail(
        cls,
        db: Session,
        user: User,
        match_id: uuid.UUID,
    ) -> JobMatchResponse:
        """Retrieve match detail, ensuring user ownership."""
        match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
        if not match:
            raise NotFoundError("Job match record not found.")

        if match.user_id != user.id:
            raise ForbiddenError("You do not have permission to access this match result.")

        return cls._format_match_response(match)

    @classmethod
    def update_match_state(
        cls,
        db: Session,
        user: User,
        match_id: uuid.UUID,
        data: JobMatchStateUpdate,
    ) -> JobMatchResponse:
        """Save or dismiss a job match."""
        match = db.query(JobMatch).filter(JobMatch.id == match_id).first()
        if not match:
            raise NotFoundError("Job match record not found.")

        if match.user_id != user.id:
            raise ForbiddenError("You do not have permission to manage this match.")

        if data.is_saved is not None:
            match.is_saved = data.is_saved
            audit_service.record_event(
                action="match.saved" if data.is_saved else "match.unsaved",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job_match",
                resource_id=str(match.id),
                metadata={"is_saved": match.is_saved},
            )

        if data.is_dismissed is not None:
            match.is_dismissed = data.is_dismissed
            audit_service.record_event(
                action="match.dismissed" if data.is_dismissed else "match.restored",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job_match",
                resource_id=str(match.id),
                metadata={"is_dismissed": match.is_dismissed},
            )

        db.commit()
        db.refresh(match)

        return cls._format_match_response(match)
