import uuid

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.job import Job
from app.models.recommendation import JobIntelligence
from app.schemas.recommendation import JobIntelligenceResponse
from app.services.ai.job_intelligence_engine import JobIntelligenceEngine


class JobIntelligenceService:
    """Manages persistent structured intelligence extracted from job descriptions."""

    @classmethod
    def get_or_create(
        cls,
        db: Session,
        job: Job,
        force_refresh: bool = False,
    ) -> JobIntelligence:
        """Fetch cached intelligence for job requisition or extract it if missing or updated."""
        content_hash = JobIntelligenceEngine.compute_content_hash(job)

        existing = (
            db.query(JobIntelligence)
            .filter(
                JobIntelligence.job_id == job.id,
            )
            .first()
        )

        # Cache hit: existing analysis matches current content hash and completed successfully
        if (
            existing
            and existing.content_hash == content_hash
            and existing.status == "completed"
            and not force_refresh
        ):
            logger.debug(
                "Cache hit for JobIntelligence on job %s (hash: %s)", job.id, content_hash[:8]
            )
            return existing

        # Extract structured intelligence via AI or deterministic fallback
        data, provider, model, is_fallback = JobIntelligenceEngine.analyze_job(job)

        if existing:
            existing.content_hash = content_hash
            existing.provider = provider
            existing.model = model
            existing.status = "completed"
            existing.error_message = None
            existing.required_skills = data.get("required_skills", [])
            existing.preferred_skills = data.get("preferred_skills", [])
            existing.experience_requirements = data.get("experience_requirements", {})
            existing.educational_qualifications = data.get("educational_qualifications", [])
            existing.responsibilities = data.get("responsibilities", [])
            existing.tools_and_frameworks = data.get("tools_and_frameworks", [])
            existing.seniority_level = data.get("seniority_level", "fresher")
            existing.work_arrangement = data.get("work_arrangement", "unspecified")
            existing.compensation_info = data.get("compensation_info")
            existing.application_requirements = data.get("application_requirements", [])
            existing.evidence_excerpts = data.get("evidence_excerpts", {})
            existing.is_deterministic_fallback = is_fallback
            record = existing
        else:
            record = JobIntelligence(
                job_id=job.id,
                content_hash=content_hash,
                provider=provider,
                model=model,
                status="completed",
                error_message=None,
                required_skills=data.get("required_skills", []),
                preferred_skills=data.get("preferred_skills", []),
                experience_requirements=data.get("experience_requirements", {}),
                educational_qualifications=data.get("educational_qualifications", []),
                responsibilities=data.get("responsibilities", []),
                tools_and_frameworks=data.get("tools_and_frameworks", []),
                seniority_level=data.get("seniority_level", "fresher"),
                work_arrangement=data.get("work_arrangement", "unspecified"),
                compensation_info=data.get("compensation_info"),
                application_requirements=data.get("application_requirements", []),
                evidence_excerpts=data.get("evidence_excerpts", {}),
                is_deterministic_fallback=is_fallback,
                metadata_json={},
            )
            db.add(record)

        db.commit()
        db.refresh(record)

        audit_service.record_event(
            action="job_intelligence.extracted",
            resource_type="job_intelligence",
            resource_id=str(record.id),
            metadata={
                "job_id": str(job.id),
                "provider": provider,
                "model": model,
                "is_fallback": is_fallback,
                "skills_count": len(record.required_skills),
            },
        )

        return record

    @classmethod
    def get_by_job_id(
        cls,
        db: Session,
        job_id: uuid.UUID,
    ) -> JobIntelligenceResponse:
        """Fetch structured intelligence for a job requisition, creating it if missing."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        intelligence = cls.get_or_create(db, job)
        return JobIntelligenceResponse.model_validate(intelligence)
