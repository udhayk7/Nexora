import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import String as SAString
from sqlalchemy import cast, or_
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.config import settings
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.core.job_utils import compute_canonical_url_hash, normalize_job_title
from app.core.url_validator import (
    extract_normalized_domain,
    normalize_company_name,
    safe_check_url_status,
)
from app.models.company import Company
from app.models.job import Job, JobSource, JobVerification
from app.models.user import User
from app.schemas.company import CompanyResponse
from app.schemas.job import (
    FeedIngestRequest,
    FeedIngestResult,
    JobCreate,
    JobDetailResponse,
    JobDuplicateCheckResponse,
    JobDuplicateMatch,
    JobFreshnessType,
    JobListResponse,
    JobObservedStatusType,
    JobRecheckRequest,
    JobRecheckResponse,
    JobResponse,
    JobSourceCreate,
    JobSourceResponse,
    JobUpdate,
    JobVerificationCreate,
    JobVerificationResponse,
    JobVerifyRequest,
)


def compute_job_freshness(last_checked_at: Optional[datetime]) -> JobFreshnessType:
    """Compute job listing freshness tier based on elapsed time since last verification/check."""
    if not last_checked_at:
        return "unknown"
    now = datetime.now(timezone.utc)
    if last_checked_at.tzinfo is None:
        last_checked = last_checked_at.replace(tzinfo=timezone.utc)
    else:
        last_checked = last_checked_at
    age_seconds = (now - last_checked).total_seconds()
    if age_seconds < 0:
        return "recent"
    age_days = age_seconds / 86400.0
    if age_days <= settings.JOB_FRESHNESS_RECENT_DAYS:
        return "recent"
    if age_days <= settings.JOB_FRESHNESS_DUE_DAYS:
        return "due_for_review"
    return "stale"


class JobService:
    """Business logic for job discovery, ingestion, company association, and deduplication."""

    @staticmethod
    def _check_manage_permission(job: Job, user: User) -> None:
        """Verify user is authorized to modify or manage this job record."""
        if user.is_superuser:
            return
        if job.is_global and job.created_by_user_id != user.id:
            raise ForbiddenError("Global curated job records can only be modified by admins")
        if job.created_by_user_id is not None and job.created_by_user_id != user.id:
            raise ForbiddenError("You do not have permission to manage this job record")

    @classmethod
    def resolve_company_association(
        cls,
        db: Session,
        company_id: Optional[uuid.UUID] = None,
        company_name_hint: Optional[str] = None,
        job_url: Optional[str] = None,
    ) -> Optional[Company]:
        """Resolve company association without guessing or attaching to similar companies."""
        # 1. Explicit company ID
        if company_id:
            comp = (
                db.query(Company)
                .filter(Company.id == company_id, Company.is_merged.is_(False))
                .first()
            )
            if comp:
                return comp

        # 2. Match by exact normalized domain from job URL
        if job_url:
            domain = extract_normalized_domain(job_url)
            if domain:
                matches = (
                    db.query(Company)
                    .filter(
                        Company.is_merged.is_(False),
                        Company.normalized_domain == domain,
                    )
                    .all()
                )
                if len(matches) == 1:
                    return matches[0]

        # 3. Match by unambiguous normalized company name hint
        if company_name_hint and company_name_hint.strip():
            norm_name = normalize_company_name(company_name_hint.strip())
            if norm_name:
                matches = (
                    db.query(Company)
                    .filter(
                        Company.is_merged.is_(False),
                        Company.normalized_name == norm_name,
                    )
                    .all()
                )
                if len(matches) == 1:
                    return matches[0]

        # In all uncertain or ambiguous scenarios, return None (unassociated job)
        return None

    @classmethod
    def _format_job_response(cls, job: Job) -> JobResponse:
        """Map Job SQLAlchemy entity to JobResponse schema."""
        sources_count = len(job.sources) if job.sources else 0
        company_resp: Optional[CompanyResponse] = None

        if job.company:
            comp_sources_count = len(job.company.sources) if job.company.sources else 0
            company_resp = CompanyResponse(
                id=job.company.id,
                name=job.company.name,
                normalized_name=job.company.normalized_name,
                website_url=job.company.website_url,
                normalized_domain=job.company.normalized_domain,
                category=job.company.category,  # type: ignore[arg-type]
                headquarters_country=job.company.headquarters_country,
                headquarters_city=job.company.headquarters_city,
                operating_regions=job.company.operating_regions or [],
                industry_tags=job.company.industry_tags or [],
                technology_tags=job.company.technology_tags or [],
                size_band=job.company.size_band,
                careers_url=job.company.careers_url,
                description=job.company.description,
                primary_source=job.company.primary_source,
                primary_source_url=job.company.primary_source_url,
                verification_status=job.company.verification_status,  # type: ignore[arg-type]
                verification_notes=job.company.verification_notes,
                last_verified_at=job.company.last_verified_at,
                created_by_user_id=job.company.created_by_user_id,
                is_global=job.company.is_global,
                is_merged=job.company.is_merged,
                merged_into_company_id=job.company.merged_into_company_id,
                metadata_json=job.company.metadata_json or {},
                created_at=job.company.created_at,
                updated_at=job.company.updated_at,
                sources_count=comp_sources_count,
            )

        freshness = compute_job_freshness(job.last_checked_at)

        return JobResponse(
            id=job.id,
            title=job.title,
            normalized_title=job.normalized_title,
            description=job.description,
            company_id=job.company_id,
            company_name=job.company.name if job.company else None,
            employment_type=job.employment_type,
            seniority_level=job.seniority_level,
            work_arrangement=job.work_arrangement,  # type: ignore[arg-type]
            location_text=job.location_text,
            city=job.city,
            state_province=job.state_province,
            country=job.country,
            remote_eligibility_regions=job.remote_eligibility_regions or [],
            skills_tags=job.skills_tags or [],
            role_family=job.role_family,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            job_url=job.job_url,
            application_url=job.application_url,
            external_source_id=job.external_source_id,
            canonical_url_hash=job.canonical_url_hash,
            source_published_at=job.source_published_at,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            last_checked_at=job.last_checked_at,
            freshness=freshness,
            job_status=job.job_status,  # type: ignore[arg-type]
            verification_status=job.verification_status,  # type: ignore[arg-type]
            verification_notes=job.verification_notes,
            last_verified_at=job.last_verified_at,
            created_by_user_id=job.created_by_user_id,
            is_global=job.is_global,
            metadata_json=job.metadata_json or {},
            created_at=job.created_at,
            updated_at=job.updated_at,
            sources_count=sources_count,
            company=company_resp,
        )

    @classmethod
    def check_duplicates(
        cls,
        db: Session,
        job_url: str,
        title: Optional[str] = None,
        company_id: Optional[uuid.UUID] = None,
    ) -> JobDuplicateCheckResponse:
        """Scan active job listings for potential duplicate matches."""
        canonical_hash = compute_canonical_url_hash(job_url)
        matches: list[JobDuplicateMatch] = []
        seen_ids: set[uuid.UUID] = set()

        # 1. Exact canonical URL match (High confidence)
        if canonical_hash:
            url_matches = (
                db.query(Job)
                .filter(
                    Job.canonical_url_hash == canonical_hash,
                    Job.job_status != "closed",
                )
                .all()
            )
            for jm in url_matches:
                seen_ids.add(jm.id)
                matches.append(
                    JobDuplicateMatch(
                        job=cls._format_job_response(jm),
                        confidence="high",
                        reason="Identical canonical job URL",
                    )
                )

        # 2. Company + Title match (Medium confidence)
        if company_id and title and title.strip():
            norm_title = normalize_job_title(title.strip())
            title_matches = (
                db.query(Job)
                .filter(
                    Job.company_id == company_id,
                    Job.normalized_title == norm_title,
                    Job.job_status != "closed",
                )
                .all()
            )
            for tm in title_matches:
                if tm.id not in seen_ids:
                    seen_ids.add(tm.id)
                    matches.append(
                        JobDuplicateMatch(
                            job=cls._format_job_response(tm),
                            confidence="medium",
                            reason=f"Same company with matching normalized title: '{norm_title}'",
                        )
                    )

        return JobDuplicateCheckResponse(matches=matches)

    @classmethod
    def create_job(
        cls,
        db: Session,
        user: User,
        data: JobCreate,
    ) -> JobDetailResponse:
        """Create a new job opportunity record with provenance citation."""
        norm_title = normalize_job_title(data.title)
        canon_hash = compute_canonical_url_hash(data.job_url)

        # Associate company safely without assumptions
        resolved_company = cls.resolve_company_association(
            db=db,
            company_id=data.company_id,
            company_name_hint=data.company_name,
            job_url=data.job_url,
        )

        job = Job(
            title=data.title.strip(),
            normalized_title=norm_title,
            description=data.description.strip(),
            company_id=resolved_company.id if resolved_company else None,
            employment_type=data.employment_type,
            seniority_level=data.seniority_level,
            work_arrangement=data.work_arrangement,
            location_text=data.location_text,
            city=data.city,
            state_province=data.state_province,
            country=data.country,
            remote_eligibility_regions=data.remote_eligibility_regions,
            skills_tags=data.skills_tags,
            role_family=data.role_family,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency,
            salary_period=data.salary_period,
            job_url=data.job_url,
            application_url=data.application_url,
            external_source_id=data.external_source_id,
            canonical_url_hash=canon_hash,
            source_published_at=data.source_published_at,
            job_status="active",
            verification_status="unverified",
            created_by_user_id=user.id,
            is_global=user.is_superuser,
        )

        db.add(job)
        db.flush()

        # Add initial discovery source citation
        if data.initial_source:
            init_src = JobSource(
                job_id=job.id,
                source_name=data.initial_source.source_name,
                source_type=data.initial_source.source_type,
                source_url=data.initial_source.source_url or data.job_url,
                external_id=data.initial_source.external_id or data.external_source_id,
                evidence_summary=data.initial_source.evidence_summary,
                metadata_json=data.initial_source.metadata_json,
            )
            db.add(init_src)
        else:
            default_src = JobSource(
                job_id=job.id,
                source_name=f"Manual Submission ({user.full_name})",
                source_type="user_added",
                source_url=data.job_url,
                evidence_summary="Manual job opportunity entry.",
            )
            db.add(default_src)

        db.commit()
        db.refresh(job)

        audit_service.record_event(
            action="job.created",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job",
            resource_id=str(job.id),
            metadata={
                "job_title": job.title,
                "company_id": str(job.company_id) if job.company_id else None,
                "work_arrangement": job.work_arrangement,
            },
        )

        return cls.get_job_detail(db, job.id)

    @classmethod
    def get_job_detail(
        cls,
        db: Session,
        job_id: uuid.UUID,
    ) -> JobDetailResponse:
        """Fetch detailed job listing with attached company profile and provenance sources."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity record not found")

        formatted_sources = [
            JobSourceResponse.model_validate(s) for s in (job.sources or [])
        ]
        formatted_verifications = [
            JobVerificationResponse.model_validate(v) for v in (job.verification_history or [])
        ]
        resp_base = cls._format_job_response(job)
        return JobDetailResponse(
            **resp_base.model_dump(),
            sources=formatted_sources,
            verification_history=formatted_verifications,
        )

    @classmethod
    def list_jobs(
        cls,
        db: Session,
        search: Optional[str] = None,
        company_id: Optional[uuid.UUID] = None,
        role_family: Optional[str] = None,
        skills: Optional[str] = None,
        seniority: Optional[str] = None,
        location: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        verification_status: Optional[str] = None,
        freshness: Optional[str] = None,
        job_status: Optional[str] = "active",
        unassociated_only: bool = False,
        user_only: bool = False,
        current_user: Optional[User] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> JobListResponse:
        """Retrieve paginated and filtered job opportunities."""
        query = db.query(Job)

        if job_status and job_status != "all":
            query = query.filter(Job.job_status == job_status)

        if unassociated_only:
            query = query.filter(Job.company_id.is_(None))
        elif company_id:
            query = query.filter(Job.company_id == company_id)

        if role_family and role_family != "all":
            query = query.filter(Job.role_family == role_family)

        if work_arrangement and work_arrangement != "all":
            query = query.filter(Job.work_arrangement == work_arrangement)

        if seniority and seniority != "all":
            query = query.filter(Job.seniority_level == seniority)

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

        if user_only and current_user:
            query = query.filter(Job.created_by_user_id == current_user.id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            norm_term = f"%{normalize_job_title(search.strip())}%"
            query = query.filter(
                or_(
                    Job.title.ilike(term),
                    Job.normalized_title.ilike(norm_term),
                    Job.location_text.ilike(term),
                    Job.city.ilike(term),
                    Job.country.ilike(term),
                    Job.description.ilike(term),
                )
            )

        if location and location.strip():
            loc_term = f"%{location.strip()}%"
            query = query.filter(
                or_(
                    Job.location_text.ilike(loc_term),
                    Job.city.ilike(loc_term),
                    Job.state_province.ilike(loc_term),
                    Job.country.ilike(loc_term),
                )
            )

        if skills and skills.strip():
            skill_term = f"%{skills.strip()}%"
            query = query.filter(cast(Job.skills_tags, SAString).ilike(skill_term))

        total = query.count()
        safe_per_page = max(1, min(per_page, 100))
        total_pages = math.ceil(total / safe_per_page) if total > 0 else 1
        safe_page = max(1, min(page, max(1, total_pages)))

        records = (
            query.order_by(Job.first_seen_at.desc())
            .offset((safe_page - 1) * safe_per_page)
            .limit(safe_per_page)
            .all()
        )

        items = [cls._format_job_response(j) for j in records]
        return JobListResponse(
            items=items,
            total=total,
            page=safe_page,
            per_page=safe_per_page,
            total_pages=total_pages,
        )

    @classmethod
    def update_job(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        data: JobUpdate,
    ) -> JobDetailResponse:
        """Update job listing metadata with authorization enforcement."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        cls._check_manage_permission(job, user)
        update_dict = data.model_dump(exclude_unset=True)

        if "title" in update_dict and update_dict["title"]:
            job.title = update_dict["title"].strip()
            job.normalized_title = normalize_job_title(job.title)

        if "job_url" in update_dict and update_dict["job_url"]:
            job.job_url = update_dict["job_url"]
            job.canonical_url_hash = compute_canonical_url_hash(job.job_url)

        if "company_id" in update_dict:
            comp_id = update_dict["company_id"]
            if comp_id:
                comp = (
                    db.query(Company)
                    .filter(Company.id == comp_id, Company.is_merged.is_(False))
                    .first()
                )
                if not comp:
                    raise BadRequestError("Associated company record does not exist or was merged")
            job.company_id = comp_id

        for field in [
            "description",
            "employment_type",
            "seniority_level",
            "work_arrangement",
            "location_text",
            "city",
            "state_province",
            "country",
            "remote_eligibility_regions",
            "skills_tags",
            "role_family",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_period",
            "application_url",
            "job_status",
        ]:
            if field in update_dict:
                setattr(job, field, update_dict[field])

        db.commit()
        db.refresh(job)

        audit_service.record_event(
            action="job.updated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job",
            resource_id=str(job.id),
            metadata={"updated_fields": list(update_dict.keys())},
        )

        return cls.get_job_detail(db, job.id)

    @classmethod
    def verify_job(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        data: JobVerifyRequest,
    ) -> JobDetailResponse:
        """Update job verification or status; requires evidence notes for verified states."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        cls._check_manage_permission(job, user)

        if data.verification_status in {"verified", "corroborated"} and (
            not data.verification_notes or len(data.verification_notes.strip()) < 5
        ):
            raise BadRequestError(
                "Verification notes with concrete evidence rationale are required"
            )

        now = datetime.now(timezone.utc)
        if data.verification_status:
            job.verification_status = data.verification_status
        if data.job_status:
            job.job_status = data.job_status

        job.verification_notes = data.verification_notes.strip()
        job.last_verified_at = now
        job.last_checked_at = now

        # Create audit JobVerification record in history
        verification_record = JobVerification(
            job_id=job.id,
            verifier_type="user",
            verifier_user_id=user.id,
            evidence_type="user_evidence",
            evidence_summary=data.verification_notes.strip(),
            observed_status="active" if job.job_status != "closed" else "closed",
            verification_outcome=job.verification_status,
            reason=data.verification_notes.strip(),
            checked_at=now,
        )
        db.add(verification_record)

        db.commit()
        db.refresh(job)

        audit_service.record_event(
            action="job.verified",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job",
            resource_id=str(job.id),
            metadata={
                "verification_status": job.verification_status,
                "job_status": job.job_status,
                "verification_id": str(verification_record.id),
            },
        )

        return cls.get_job_detail(db, job.id)

    @classmethod
    def submit_verification_evidence(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        data: JobVerificationCreate,
    ) -> JobDetailResponse:
        """Submit concrete verification evidence notes and evaluation for a job listing."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        cls._check_manage_permission(job, user)

        if not data.reason or len(data.reason.strip()) < 5:
            raise BadRequestError("Mandatory evidence rationale must be at least 5 characters")

        now = datetime.now(timezone.utc)

        # Create immutable verification record
        verification_record = JobVerification(
            job_id=job.id,
            verifier_type="user",
            verifier_user_id=user.id,
            evidence_type=data.evidence_type,
            evidence_url=data.evidence_url,
            evidence_summary=data.evidence_summary or data.reason,
            observed_status=data.observed_status,
            verification_outcome=data.verification_outcome,
            reason=data.reason.strip(),
            checked_at=now,
            metadata_json=data.metadata_json or {},
        )
        db.add(verification_record)

        # Update Job denormalized verification state
        job.verification_status = data.verification_outcome
        job.verification_notes = data.reason.strip()
        job.last_verified_at = now
        job.last_checked_at = now
        if data.observed_status in {"closed", "removed", "expired"}:
            job.job_status = "closed"
        elif data.observed_status == "active" and job.job_status == "closed":
            job.job_status = "active"

        db.commit()
        db.refresh(job)

        audit_service.record_event(
            action="job.evidence_submitted",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job",
            resource_id=str(job.id),
            metadata={
                "verification_outcome": job.verification_status,
                "evidence_type": data.evidence_type,
                "observed_status": data.observed_status,
                "verification_id": str(verification_record.id),
            },
        )

        return cls.get_job_detail(db, job.id)

    @classmethod
    def recheck_job(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        request: JobRecheckRequest,
    ) -> JobRecheckResponse:
        """Execute a safe availability recheck of a job listing using SSRF-safe guards."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        target_url = job.job_url or job.application_url
        if not target_url:
            raise BadRequestError("Job has no target URL configured for rechecking")

        now = datetime.now(timezone.utc)

        # Connection-time SSRF safe check
        is_reachable, status_code, message = safe_check_url_status(target_url)

        if not is_reachable and "Security" in message:
            ver_record = JobVerification(
                job_id=job.id,
                verifier_type="system",
                verifier_user_id=user.id,
                evidence_type="other",
                evidence_url=target_url,
                evidence_summary="Security violation blocked by SSRF protection",
                observed_status="unknown",
                verification_outcome="suspicious",
                reason=f"Security alert: {message}",
                checked_at=now,
                metadata_json={"security_block": True},
            )
            db.add(ver_record)
            job.last_checked_at = now
            job.verification_status = "suspicious"
            db.commit()
            db.refresh(ver_record)

            audit_service.record_event(
                action="job.recheck_blocked",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job",
                resource_id=str(job.id),
                metadata={"reason": message},
            )

            return JobRecheckResponse(
                job_id=job.id,
                recheck_status="failed",
                observed_status="unknown",
                freshness=compute_job_freshness(job.last_checked_at),
                status_code=status_code,
                message=message,
                verification=JobVerificationResponse.model_validate(ver_record),
            )

        if is_reachable:
            observed: JobObservedStatusType = "active"
            outcome = job.verification_status
            summary = request.evidence_summary or f"Automated HTTP check succeeded ({message})"
            reason_str = (
                f"Safe HTTP availability check confirmed listing is reachable (HTTP {status_code})."
            )

            ver_record = JobVerification(
                job_id=job.id,
                verifier_type="system",
                verifier_user_id=user.id,
                evidence_type="careers_page",
                evidence_url=target_url,
                evidence_summary=summary,
                observed_status=observed,
                verification_outcome=outcome,
                reason=reason_str,
                checked_at=now,
                metadata_json={"http_status": status_code},
            )
            db.add(ver_record)
            job.last_checked_at = now
            if job.job_status == "closed":
                job.job_status = "active"
            db.commit()
            db.refresh(ver_record)

            audit_service.record_event(
                action="job.rechecked",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job",
                resource_id=str(job.id),
                metadata={"status_code": status_code, "is_reachable": True},
            )

            return JobRecheckResponse(
                job_id=job.id,
                recheck_status="completed",
                observed_status=observed,
                freshness=compute_job_freshness(job.last_checked_at),
                status_code=status_code,
                message=message,
                verification=JobVerificationResponse.model_validate(ver_record),
            )

        elif status_code in {404, 410}:
            observed = "removed" if status_code == 404 else "expired"
            outcome = "expired"
            reason_str = (
                f"Target listing returned HTTP {status_code} ({message}). "
                "Listing is no longer active."
            )

            ver_record = JobVerification(
                job_id=job.id,
                verifier_type="system",
                verifier_user_id=user.id,
                evidence_type="careers_page",
                evidence_url=target_url,
                evidence_summary=message,
                observed_status=observed,
                verification_outcome=outcome,
                reason=reason_str,
                checked_at=now,
                metadata_json={"http_status": status_code},
            )
            db.add(ver_record)
            job.last_checked_at = now
            job.job_status = "closed"
            db.commit()
            db.refresh(ver_record)

            audit_service.record_event(
                action="job.rechecked",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job",
                resource_id=str(job.id),
                metadata={"status_code": status_code, "is_reachable": False},
            )

            return JobRecheckResponse(
                job_id=job.id,
                recheck_status="completed",
                observed_status=observed,
                freshness=compute_job_freshness(job.last_checked_at),
                status_code=status_code,
                message=message,
                verification=JobVerificationResponse.model_validate(ver_record),
            )

        else:
            ver_record = JobVerification(
                job_id=job.id,
                verifier_type="system",
                verifier_user_id=user.id,
                evidence_type="other",
                evidence_url=target_url,
                evidence_summary=message,
                observed_status="unknown",
                verification_outcome=job.verification_status,
                reason=(
                    f"Automated recheck inconclusive ({message}). "
                    "Manual evidence submission is recommended."
                ),
                checked_at=now,
                metadata_json={"http_status": status_code, "error": message},
            )
            db.add(ver_record)
            job.last_checked_at = now
            db.commit()
            db.refresh(ver_record)

            audit_service.record_event(
                action="job.recheck_inconclusive",
                actor_type="user",
                actor_id=str(user.id),
                resource_type="job",
                resource_id=str(job.id),
                metadata={"status_code": status_code, "error": message},
            )

            return JobRecheckResponse(
                job_id=job.id,
                recheck_status="manual_evidence_required",
                observed_status="unknown",
                freshness=compute_job_freshness(job.last_checked_at),
                status_code=status_code,
                message=f"{message}. Manual evidence submission is recommended.",
                verification=JobVerificationResponse.model_validate(ver_record),
            )

    @classmethod
    def get_verification_history(
        cls,
        db: Session,
        job_id: uuid.UUID,
    ) -> list[JobVerificationResponse]:
        """Fetch immutable history of all verification checks for a job listing."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        verifications = (
            db.query(JobVerification)
            .filter(JobVerification.job_id == job_id)
            .order_by(JobVerification.checked_at.desc())
            .all()
        )
        return [JobVerificationResponse.model_validate(v) for v in verifications]

    @classmethod
    def add_source(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        data: JobSourceCreate,
    ) -> JobSourceResponse:
        """Attach a new discovery provenance source to a job listing."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        cls._check_manage_permission(job, user)

        source = JobSource(
            job_id=job.id,
            source_name=data.source_name.strip(),
            source_type=data.source_type,
            source_url=data.source_url or job.job_url,
            external_id=data.external_id,
            evidence_summary=data.evidence_summary,
            metadata_json=data.metadata_json,
        )

        db.add(source)
        job.last_seen_at = datetime.now(timezone.utc)
        job.last_checked_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(source)

        audit_service.record_event(
            action="job.source_added",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job_source",
            resource_id=str(source.id),
            metadata={"job_id": str(job.id), "source_type": source.source_type},
        )

        return JobSourceResponse.model_validate(source)

    @classmethod
    def delete_source(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        """Remove a provenance citation."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job record not found")

        cls._check_manage_permission(job, user)

        source = (
            db.query(JobSource)
            .filter(JobSource.id == source_id, JobSource.job_id == job_id)
            .first()
        )
        if not source:
            raise NotFoundError("Job source record not found")

        db.delete(source)
        db.commit()

        audit_service.record_event(
            action="job.source_deleted",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job_source",
            resource_id=str(source_id),
            metadata={"job_id": str(job.id)},
        )

    @classmethod
    def ingest_feed(
        cls,
        db: Session,
        user: User,
        data: FeedIngestRequest,
    ) -> FeedIngestResult:
        """Batch-ingest structured job opportunities from permitted feeds idempotently."""
        created_count = 0
        updated_count = 0
        errors: list[dict[str, Any]] = []

        now = datetime.now(timezone.utc)

        for idx, rec in enumerate(data.records):
            try:
                canon_hash = compute_canonical_url_hash(rec.job_url)

                # Check if job already exists via canonical URL hash or external source ID
                existing_job: Optional[Job] = None
                if canon_hash:
                    existing_job = (
                        db.query(Job)
                        .filter(Job.canonical_url_hash == canon_hash)
                        .first()
                    )

                if (
                    not existing_job
                    and rec.external_source_id
                    and rec.external_source_id.strip()
                ):
                    existing_job = (
                        db.query(Job)
                        .filter(Job.external_source_id == rec.external_source_id.strip())
                        .first()
                    )

                if existing_job:
                    # Update timestamps idempotently
                    existing_job.last_seen_at = now
                    existing_job.last_checked_at = now

                    # Re-associate company if existing was unassociated and new info matches
                    if not existing_job.company_id:
                        resolved_comp = cls.resolve_company_association(
                            db=db,
                            company_id=rec.company_id,
                            company_name_hint=rec.company_name,
                            job_url=rec.job_url,
                        )
                        if resolved_comp:
                            existing_job.company_id = resolved_comp.id

                    # Attach feed citation if not already present
                    src_exists = (
                        db.query(JobSource)
                        .filter(
                            JobSource.job_id == existing_job.id,
                            JobSource.source_name == data.feed_name,
                        )
                        .first()
                    )
                    if not src_exists:
                        db.add(
                            JobSource(
                                job_id=existing_job.id,
                                source_name=data.feed_name,
                                source_type=data.source_type,
                                source_url=data.source_url or rec.job_url,
                                external_id=rec.external_source_id,
                                evidence_summary="Observed via permitted feed sync.",
                                first_seen_at=now,
                                last_seen_at=now,
                            )
                        )
                    updated_count += 1
                else:
                    # Create new job
                    norm_title = normalize_job_title(rec.title)
                    resolved_company = cls.resolve_company_association(
                        db=db,
                        company_id=rec.company_id,
                        company_name_hint=rec.company_name,
                        job_url=rec.job_url,
                    )

                    new_job = Job(
                        title=rec.title.strip(),
                        normalized_title=norm_title,
                        description=rec.description.strip(),
                        company_id=resolved_company.id if resolved_company else None,
                        employment_type=rec.employment_type,
                        seniority_level=rec.seniority_level,
                        work_arrangement=rec.work_arrangement,
                        location_text=rec.location_text,
                        city=rec.city,
                        state_province=rec.state_province,
                        country=rec.country,
                        remote_eligibility_regions=rec.remote_eligibility_regions,
                        skills_tags=rec.skills_tags,
                        role_family=rec.role_family,
                        salary_min=rec.salary_min,
                        salary_max=rec.salary_max,
                        salary_currency=rec.salary_currency,
                        salary_period=rec.salary_period,
                        job_url=rec.job_url,
                        application_url=rec.application_url,
                        external_source_id=rec.external_source_id,
                        canonical_url_hash=canon_hash,
                        source_published_at=rec.source_published_at,
                        first_seen_at=now,
                        last_seen_at=now,
                        last_checked_at=now,
                        job_status="active",
                        verification_status="corroborated"
                        if data.source_type == "official_api"
                        else "unverified",
                        created_by_user_id=user.id,
                        is_global=user.is_superuser,
                    )
                    db.add(new_job)
                    db.flush()

                    db.add(
                        JobSource(
                            job_id=new_job.id,
                            source_name=data.feed_name,
                            source_type=data.source_type,
                            source_url=data.source_url or rec.job_url,
                            external_id=rec.external_source_id,
                            evidence_summary=f"Ingested via feed '{data.feed_name}'.",
                            first_seen_at=now,
                            last_seen_at=now,
                        )
                    )
                    created_count += 1

            except Exception as e:
                errors.append({"record_index": idx, "error": str(e)})

        db.commit()

        audit_service.record_event(
            action="job.feed_ingested",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="job_feed",
            resource_id=data.feed_name,
            metadata={
                "feed_name": data.feed_name,
                "total_processed": len(data.records),
                "created_count": created_count,
                "updated_count": updated_count,
                "errors_count": len(errors),
            },
        )

        return FeedIngestResult(
            feed_name=data.feed_name,
            total_processed=len(data.records),
            created_count=created_count,
            updated_count=updated_count,
            errors_count=len(errors),
            errors=errors,
        )
