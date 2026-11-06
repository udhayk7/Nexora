import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.models.analysis import ResumeAnalysis
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.services.ai.base import AIProviderError
from app.services.ai.factory import get_ai_provider


class ResumeAnalysisService:
    """Service orchestrating evidence-grounded AI resume intelligence analysis."""

    def analyze_version(
        self,
        db: Session,
        current_user: User,
        resume_id: uuid.UUID,
        version_id: uuid.UUID,
        force_refresh: bool = False,
        provider_name: Optional[str] = None,
    ) -> ResumeAnalysis:
        """
        Analyze a specific resume version using the configured AI provider.
        Enforces user ownership, deduplication, audit trails, and strict evidence grounding.
        """
        # Verify user ownership
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
            .first()
        )
        if not resume:
            raise NotFoundError("Resume not found")

        version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.id == version_id, ResumeVersion.resume_id == resume.id)
            .first()
        )
        if not version:
            raise NotFoundError("Resume version not found")

        if not version.raw_text or not version.raw_text.strip():
            raise BadRequestError(
                "Cannot analyze resume without extracted text content. "
                "The document may be scanned or empty."
            )

        provider = get_ai_provider(provider_name)

        # Cache / Deduplication: return existing completed analysis unless force_refresh requested
        if not force_refresh:
            existing = (
                db.query(ResumeAnalysis)
                .filter(
                    ResumeAnalysis.version_id == version.id,
                    ResumeAnalysis.provider == provider.name,
                    ResumeAnalysis.model == provider.model_name,
                    ResumeAnalysis.status == "completed",
                )
                .order_by(ResumeAnalysis.created_at.desc())
                .first()
            )
            if existing:
                logger.info(f"Returning cached analysis {existing.id} for version {version.id}")
                return existing

        # Create persistent analysis record in processing state
        analysis_id = uuid.uuid4()
        analysis = ResumeAnalysis(
            id=analysis_id,
            user_id=current_user.id,
            resume_id=resume.id,
            version_id=version.id,
            status="processing",
            provider=provider.name,
            model=provider.model_name,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        audit_service.record_event(
            action="resume.analysis_requested",
            resource_type="resume_analysis",
            actor_type="user",
            actor_id=str(current_user.id),
            resource_id=str(analysis.id),
            metadata={
                "resume_id": str(resume.id),
                "version_id": str(version.id),
                "provider": provider.name,
                "model": provider.model_name,
            },
        )

        try:
            ai_response = provider.analyze_resume(
                resume_text=version.raw_text,
                structured_sections=version.parsed_content,
            )

            analysis.status = "completed"
            analysis.result = ai_response.result.model_dump()
            analysis.prompt_tokens = ai_response.prompt_tokens
            analysis.completion_tokens = ai_response.completion_tokens
            analysis.total_tokens = ai_response.total_tokens
            analysis.estimated_cost_usd = ai_response.estimated_cost_usd
            analysis.completed_at = datetime.now(timezone.utc)
            analysis.error_summary = None

            db.commit()
            db.refresh(analysis)

            audit_service.record_event(
                action="resume.analysis_completed",
                resource_type="resume_analysis",
                actor_type="user",
                actor_id=str(current_user.id),
                resource_id=str(analysis.id),
                metadata={
                    "provider": provider.name,
                    "model": provider.model_name,
                    "total_tokens": ai_response.total_tokens,
                },
            )

            logger.info(f"Successfully completed AI analysis {analysis.id} for resume {resume.id}")
            return analysis

        except Exception as exc:
            analysis.status = "failed"
            analysis.error_summary = str(exc)[:500]
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()

            audit_service.record_event(
                action="resume.analysis_failed",
                resource_type="resume_analysis",
                actor_type="user",
                actor_id=str(current_user.id),
                resource_id=str(analysis.id),
                metadata={
                    "provider": provider.name,
                    "error": str(exc)[:100],
                },
            )

            if isinstance(exc, AIProviderError):
                raise exc

            raise AIProviderError(f"Resume analysis failed: {str(exc)[:100]}") from exc

    def list_analyses(
        self,
        db: Session,
        current_user: User,
        resume_id: uuid.UUID,
    ) -> list[ResumeAnalysis]:
        """List all analyses for a specific resume owned by the current user."""
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
            .first()
        )
        if not resume:
            raise NotFoundError("Resume not found")

        return (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.resume_id == resume.id,
                ResumeAnalysis.user_id == current_user.id,
            )
            .order_by(ResumeAnalysis.created_at.desc())
            .all()
        )

    def get_analysis(
        self,
        db: Session,
        current_user: User,
        resume_id: uuid.UUID,
        analysis_id: uuid.UUID,
    ) -> ResumeAnalysis:
        """Retrieve a specific analysis with ownership verification."""
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
            .first()
        )
        if not resume:
            raise NotFoundError("Resume not found")

        analysis = (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.id == analysis_id,
                ResumeAnalysis.resume_id == resume.id,
                ResumeAnalysis.user_id == current_user.id,
            )
            .first()
        )
        if not analysis:
            raise NotFoundError("Resume analysis not found")

        return analysis


# Global analysis service instance
analysis_service = ResumeAnalysisService()
