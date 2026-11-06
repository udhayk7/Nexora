import copy
import re
import uuid
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.core.storage import storage_service
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.tailoring import ResumeTailoringChange, ResumeTailoringSession
from app.schemas.job import JobResponse
from app.schemas.tailoring import (
    BatchChangeActionRequest,
    ChangeStatusUpdateRequest,
    CompilePDFResponse,
    JobRequirementAnalysis,
    SaveTailoredVersionRequest,
    TailoringChangeResponse,
    TailoringSessionCreateRequest,
    TailoringSessionResponse,
    TailoringSessionSummaryResponse,
    UpdateContentRequest,
)
from app.services.latex_compiler import compile_resume_to_pdf, validate_latex_security
from app.services.latex_generator import generate_latex_resume
from app.services.tailoring_analyzer import TailoringAnalyzer
from app.services.tailoring_engine import TailoringEngine


class TailoringService:
    """
    Domain service for managing interactive job-specific resume tailoring sessions,
    grounded change reviews, LaTeX code editing, and immutable tailored version creation.
    """

    @classmethod
    def create_session(
        cls,
        db: Session,
        user_id: uuid.UUID,
        req: TailoringSessionCreateRequest,
    ) -> TailoringSessionResponse:
        """Create and initialize a new tailoring session for a given job and resume version."""
        # 1. Verify target job exists
        job = db.get(Job, req.job_id)
        if not job:
            raise NotFoundError(f"Job opportunity with ID {req.job_id} not found.")

        # 2. Verify resume ownership
        resume = db.get(Resume, req.resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError(f"Resume with ID {req.resume_id} not found.")

        # 3. Resolve base resume version
        base_version: Optional[ResumeVersion] = None
        if req.version_id:
            base_version = db.get(ResumeVersion, req.version_id)
            if not base_version or base_version.resume_id != resume.id:
                raise NotFoundError(f"Resume version with ID {req.version_id} not found.")
        else:
            # Pick latest or current version
            if resume.current_version_id:
                base_version = db.get(ResumeVersion, resume.current_version_id)
            if not base_version:
                stmt = (
                    select(ResumeVersion)
                    .where(ResumeVersion.resume_id == resume.id)
                    .order_by(desc(ResumeVersion.version_number))
                    .limit(1)
                )
                base_version = db.scalars(stmt).first()

        if not base_version:
            raise BadRequestError("Cannot tailor a resume without any uploaded versions.")

        # 4. Generate initial LaTeX source from candidate's parsed resume
        parsed_content = base_version.parsed_content or {}
        comp_name = job.company.name if job.company else None
        initial_latex = generate_latex_resume(
            parsed_content,
            job_title=job.title,
            company_name=comp_name,
        )

        # 5. Run grounded requirement analysis (strictly zero fabrication)
        analysis: JobRequirementAnalysis = TailoringAnalyzer.analyze_requirements(job, base_version)

        # 6. Create Tailoring Session record
        session = ResumeTailoringSession(
            id=uuid.uuid4(),
            user_id=user_id,
            resume_id=resume.id,
            version_id=base_version.id,
            job_id=job.id,
            status="ready",
            job_analysis=analysis.model_dump(),
            latex_content=initial_latex,
        )
        db.add(session)
        db.flush()

        # 7. Generate proposed grounded modifications
        proposed_changes, provider_name, model_name = TailoringEngine.generate_changes(
            job,
            base_version,
            analysis,
        )
        session.provider = provider_name
        session.model = model_name

        for idx, pc in enumerate(proposed_changes):
            change_rec = ResumeTailoringChange(
                id=uuid.uuid4(),
                session_id=session.id,
                section_name=pc.section_name,
                change_type=pc.change_type,
                original_content=pc.original_content,
                proposed_content=pc.proposed_content,
                reason=pc.reason,
                supporting_evidence=pc.supporting_evidence,
                related_job_requirement=pc.related_job_requirement,
                confidence_level=pc.confidence_level,
                status="pending",
                order_index=idx,
            )
            db.add(change_rec)

        db.commit()
        db.refresh(session)

        audit_service.record_event(
            action="tailoring.session_created",
            resource_type="resume_tailoring_session",
            resource_id=str(session.id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={
                "job_id": str(job.id),
                "resume_id": str(resume.id),
                "version_id": str(base_version.id),
                "changes_count": len(proposed_changes),
            },
        )

        return cls.get_session(db, session.id, user_id)

    @classmethod
    def get_session(
        cls,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TailoringSessionResponse:
        """Fetch complete tailoring workspace state including job, changes, and active LaTeX."""
        stmt = (
            select(ResumeTailoringSession)
            .where(
                ResumeTailoringSession.id == session_id,
                ResumeTailoringSession.user_id == user_id,
            )
            .options(
                selectinload(ResumeTailoringSession.changes),
                selectinload(ResumeTailoringSession.job).selectinload(Job.company),
                selectinload(ResumeTailoringSession.resume),
                selectinload(ResumeTailoringSession.version),
            )
        )
        session = db.scalars(stmt).first()
        if not session:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        return cls._format_session_response(session)

    @classmethod
    def list_user_sessions(
        cls,
        db: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TailoringSessionSummaryResponse]:
        """List past tailoring sessions for the authenticated user."""
        stmt = (
            select(ResumeTailoringSession)
            .where(ResumeTailoringSession.user_id == user_id)
            .options(
                selectinload(ResumeTailoringSession.changes),
                selectinload(ResumeTailoringSession.job).selectinload(Job.company),
                selectinload(ResumeTailoringSession.resume),
            )
            .order_by(desc(ResumeTailoringSession.updated_at))
            .offset(skip)
            .limit(limit)
        )
        sessions = db.scalars(stmt).all()

        summaries: list[TailoringSessionSummaryResponse] = []
        for s in sessions:
            job_title = s.job.title if s.job else "Target Role"
            company_name = s.job.company.name if s.job and s.job.company else "Company"
            resume_title = s.resume.title if s.resume else "Base Resume"
            total = len(s.changes)
            accepted = sum(1 for c in s.changes if c.status in ("accepted", "modified"))

            summaries.append(
                TailoringSessionSummaryResponse(
                    id=s.id,
                    resume_id=s.resume_id,
                    version_id=s.version_id,
                    job_id=s.job_id,
                    status=s.status,
                    job_title=job_title,
                    company_name=company_name,
                    resume_title=resume_title,
                    tailored_version_id=s.tailored_version_id,
                    total_changes=total,
                    accepted_changes=accepted,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )
        return summaries

    @classmethod
    def update_change_status(
        cls,
        db: Session,
        session_id: uuid.UUID,
        change_id: uuid.UUID,
        user_id: uuid.UUID,
        req: ChangeStatusUpdateRequest,
    ) -> TailoringSessionResponse:
        """Update individual change status and sync with active LaTeX."""
        stmt = (
            select(ResumeTailoringSession)
            .where(
                ResumeTailoringSession.id == session_id,
                ResumeTailoringSession.user_id == user_id,
            )
            .options(selectinload(ResumeTailoringSession.changes))
        )
        session = db.scalars(stmt).first()
        if not session:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        target_change = next((c for c in session.changes if c.id == change_id), None)
        if not target_change:
            raise NotFoundError(f"Tailoring change {change_id} not found.")

        old_status = target_change.status
        target_change.status = req.status
        if req.user_content is not None:
            target_change.user_content = req.user_content

        # Update active LaTeX in session if replacement is found
        if session.latex_content:
            session.latex_content = cls._apply_single_change_to_latex(
                latex=session.latex_content,
                change=target_change,
                new_status=req.status,
                user_content=req.user_content,
                old_status=old_status,
            )

        db.commit()

        audit_service.record_event(
            action="tailoring.change_status_updated",
            resource_type="resume_tailoring_change",
            resource_id=str(change_id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={
                "session_id": str(session_id),
                "old_status": old_status,
                "new_status": req.status,
            },
        )

        return cls.get_session(db, session_id, user_id)

    @classmethod
    def batch_update_changes(
        cls,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        req: BatchChangeActionRequest,
    ) -> TailoringSessionResponse:
        """Batch approve all suggestions or restore original resume content."""
        stmt = (
            select(ResumeTailoringSession)
            .where(
                ResumeTailoringSession.id == session_id,
                ResumeTailoringSession.user_id == user_id,
            )
            .options(
                selectinload(ResumeTailoringSession.changes),
                selectinload(ResumeTailoringSession.version),
                selectinload(ResumeTailoringSession.job).selectinload(Job.company),
            )
        )
        session = db.scalars(stmt).first()
        if not session:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        if req.action == "accept_all":
            for c in session.changes:
                if c.status != "accepted":
                    c.status = "accepted"
            # Rebuild LaTeX with all accepted changes
            session.latex_content = cls._rebuild_latex_from_changes(session)

        elif req.action == "reject_all":
            for c in session.changes:
                c.status = "rejected"
            # Reset LaTeX to base
            c_name = session.job.company.name if session.job and session.job.company else None
            session.latex_content = generate_latex_resume(
                session.version.parsed_content or {},
                job_title=session.job.title if session.job else None,
                company_name=c_name,
            )

        elif req.action == "restore_original":
            for c in session.changes:
                c.status = "rejected"
                c.user_content = None
            c_name = session.job.company.name if session.job and session.job.company else None
            session.latex_content = generate_latex_resume(
                session.version.parsed_content or {},
                job_title=session.job.title if session.job else None,
                company_name=c_name,
            )

        db.commit()

        audit_service.record_event(
            action="tailoring.batch_changes_updated",
            resource_type="resume_tailoring_session",
            resource_id=str(session_id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={"action": req.action},
        )

        return cls.get_session(db, session_id, user_id)

    @classmethod
    def update_latex_content(
        cls,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        req: UpdateContentRequest,
    ) -> TailoringSessionResponse:
        """Update and validate LaTeX content directly edited via Monaco."""
        session = db.get(ResumeTailoringSession, session_id)
        if not session or session.user_id != user_id:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        # Sandboxing & security check
        validate_latex_security(req.latex_content)

        session.latex_content = req.latex_content
        db.commit()

        audit_service.record_event(
            action="tailoring.latex_updated",
            resource_type="resume_tailoring_session",
            resource_id=str(session_id),
            actor_type="user",
            actor_id=str(user_id),
        )

        return cls.get_session(db, session_id, user_id)

    @classmethod
    def compile_pdf(
        cls,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        latex_content: Optional[str] = None,
    ) -> tuple[bytes, CompilePDFResponse]:
        """Securely compile LaTeX into PDF using sandboxed engine or fallback layout renderer."""
        stmt = (
            select(ResumeTailoringSession)
            .where(
                ResumeTailoringSession.id == session_id,
                ResumeTailoringSession.user_id == user_id,
            )
            .options(
                selectinload(ResumeTailoringSession.version),
            )
        )
        session = db.scalars(stmt).first()
        if not session:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        content_to_compile = latex_content or session.latex_content or ""
        validate_latex_security(content_to_compile)

        parsed_fallback = session.version.parsed_content if session.version else None
        pdf_bytes, page_count, engine_used = compile_resume_to_pdf(
            latex_content=content_to_compile,
            parsed_fallback=parsed_fallback,
        )

        resp = CompilePDFResponse(
            success=True,
            compilation_engine=engine_used,
            download_url=f"/api/v1/tailoring/{session_id}/pdf",
            page_count=page_count,
            disclaimer="Compiled under sandboxed controls with zero shell-escape risk.",
        )
        return pdf_bytes, resp

    @classmethod
    def save_tailored_version(
        cls,
        db: Session,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        req: SaveTailoredVersionRequest,
    ) -> ResumeVersion:
        """
        Finalize tailoring session and create an immutable tailored ResumeVersion.
        Strictly preserves original resume and parent version history.
        """
        stmt = (
            select(ResumeTailoringSession)
            .where(
                ResumeTailoringSession.id == session_id,
                ResumeTailoringSession.user_id == user_id,
            )
            .options(
                selectinload(ResumeTailoringSession.changes),
                selectinload(ResumeTailoringSession.resume).selectinload(Resume.versions),
                selectinload(ResumeTailoringSession.version),
                selectinload(ResumeTailoringSession.job).selectinload(Job.company),
            )
        )
        session = db.scalars(stmt).first()
        if not session:
            raise NotFoundError(f"Tailoring session {session_id} not found.")

        resume = session.resume
        base_version = session.version
        job = session.job

        latex_to_save = req.latex_content or session.latex_content or ""
        validate_latex_security(latex_to_save)

        # 1. Determine next version number
        next_ver_num = max((v.version_number for v in resume.versions), default=0) + 1

        # 2. Build tailored structured content from accepted changes
        tailored_parsed = cls._build_tailored_parsed_content(base_version, session.changes)

        # 3. Compile PDF and store in local storage
        new_version_id = uuid.uuid4()
        comp_name = job.company.name if job.company else "Company"
        slug_title = re.sub(r"[^\w\s-]", "", job.title).strip().replace(" ", "_").lower()
        filename = f"tailored_{slug_title}_{next_ver_num}.pdf"

        try:
            pdf_bytes, _, _ = compile_resume_to_pdf(
                latex_content=latex_to_save,
                parsed_fallback=tailored_parsed,
            )
            storage_path = storage_service.save_file(
                user_id=user_id,
                resume_id=resume.id,
                version_id=new_version_id,
                filename=filename,
                content=pdf_bytes,
            )
            file_size = len(pdf_bytes)
        except Exception as exc:
            logger.warning(f"Could not compile PDF for tailored version: {exc}")
            storage_path = base_version.storage_path
            file_size = base_version.file_size

        # 4. Count accepted modifications
        accepted_count = sum(1 for c in session.changes if c.status in ("accepted", "modified"))

        title = req.title or f"Tailored for {job.title} at {comp_name}"

        # 5. Create new immutable ResumeVersion linked to target job and parent version
        tailored_version = ResumeVersion(
            id=new_version_id,
            resume_id=resume.id,
            version_number=next_ver_num,
            parent_version_id=base_version.id,
            job_id=job.id,
            tailoring_session_id=session.id,
            is_tailored=True,
            latex_source=latex_to_save,
            pdf_storage_path=storage_path,
            original_filename=filename,
            file_type="pdf",
            file_size=file_size,
            storage_path=storage_path,
            parsing_status="parsed",
            parsed_content=tailored_parsed,
            raw_text=base_version.raw_text,
            tailoring_metadata={
                "job_id": str(job.id),
                "job_title": job.title,
                "company_name": comp_name,
                "parent_version_id": str(base_version.id),
                "parent_version_number": base_version.version_number,
                "accepted_changes_count": accepted_count,
                "version_title": title,
            },
        )
        db.add(tailored_version)

        # 6. Update session reference and status
        session.tailored_version_id = tailored_version.id
        session.status = "saved"
        session.latex_content = latex_to_save

        db.commit()
        db.refresh(tailored_version)

        audit_service.record_event(
            action="tailoring.version_saved",
            resource_type="resume_version",
            resource_id=str(tailored_version.id),
            actor_type="user",
            actor_id=str(user_id),
            metadata={
                "session_id": str(session.id),
                "resume_id": str(resume.id),
                "job_id": str(job.id),
                "version_number": next_ver_num,
                "accepted_changes": accepted_count,
            },
        )

        return tailored_version

    # --- Private Helpers ---

    @classmethod
    def _format_session_response(cls, session: ResumeTailoringSession) -> TailoringSessionResponse:
        """Format ResumeTailoringSession into full response schema."""
        change_responses: list[TailoringChangeResponse] = []
        for c in session.changes:
            if c.status == "modified" and c.user_content:
                active_content = c.user_content
            elif c.status == "accepted":
                active_content = c.proposed_content
            elif c.status == "rejected":
                active_content = c.original_content
            else:
                active_content = c.proposed_content

            change_responses.append(
                TailoringChangeResponse(
                    id=c.id,
                    session_id=c.session_id,
                    section_name=c.section_name,
                    change_type=c.change_type,
                    original_content=c.original_content,
                    proposed_content=c.proposed_content,
                    user_content=c.user_content,
                    active_content=active_content,
                    reason=c.reason,
                    supporting_evidence=c.supporting_evidence,
                    related_job_requirement=c.related_job_requirement,
                    confidence_level=c.confidence_level,
                    status=c.status,  # type: ignore
                    order_index=c.order_index,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )

        job_resp = JobResponse.model_validate(session.job) if session.job else None
        analysis_obj = (
            JobRequirementAnalysis.model_validate(session.job_analysis)
            if session.job_analysis
            else None
        )

        return TailoringSessionResponse(
            id=session.id,
            user_id=session.user_id,
            resume_id=session.resume_id,
            version_id=session.version_id,
            job_id=session.job_id,
            status=session.status,
            job_analysis=analysis_obj,
            latex_content=session.latex_content,
            tailored_version_id=session.tailored_version_id,
            provider=session.provider,
            model=session.model,
            error_summary=session.error_summary,
            changes=change_responses,
            job=job_resp,
            resume_title=session.resume.title if session.resume else None,
            parent_version_number=session.version.version_number if session.version else None,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    @classmethod
    def _apply_single_change_to_latex(
        cls,
        latex: str,
        change: ResumeTailoringChange,
        new_status: str,
        user_content: Optional[str],
        old_status: str,
    ) -> str:
        """Heuristically update active LaTeX source when an individual change is toggled."""
        if new_status in ("accepted", "modified"):
            replacement = (
                user_content
                if (new_status == "modified" and user_content)
                else change.proposed_content
            )
            # Find and replace original or prior content
            if change.original_content in latex:
                return latex.replace(change.original_content, replacement, 1)
        elif new_status == "rejected":
            # Revert replacement back to original
            prior = change.user_content or change.proposed_content
            if prior in latex:
                return latex.replace(prior, change.original_content, 1)

        return latex

    @classmethod
    def _rebuild_latex_from_changes(cls, session: ResumeTailoringSession) -> str:
        """Regenerate complete LaTeX source applying all accepted/modified changes."""
        tailored_parsed = cls._build_tailored_parsed_content(
            session.version,
            session.changes,
        )
        return generate_latex_resume(
            tailored_parsed,
            job_title=session.job.title if session.job else None,
            company_name=session.job.company.name if session.job and session.job.company else None,
        )

    @classmethod
    def _build_tailored_parsed_content(
        cls,
        base_version: ResumeVersion,
        changes: list[ResumeTailoringChange],
    ) -> dict[str, Any]:
        """Clone base parsed content and inject accepted/modified changes preserving truth."""
        parsed = copy.deepcopy(base_version.parsed_content or {})

        for c in changes:
            if c.status not in ("accepted", "modified"):
                continue

            active_text = (
                c.user_content
                if (c.status == "modified" and c.user_content)
                else c.proposed_content
            )

            if c.section_name == "summary":
                parsed["summary"] = active_text

            elif c.section_name == "skills":
                # Split comma-separated skills
                reordered = [s.strip() for s in active_text.split(",") if s.strip()]
                parsed["skills"] = reordered

            elif c.section_name == "experience":
                for exp in parsed.get("experience") or []:
                    if isinstance(exp, dict) and exp.get("bullets"):
                        bullets = exp["bullets"]
                        for i, b in enumerate(bullets):
                            if str(b).strip() == c.original_content.strip():
                                bullets[i] = active_text

            elif c.section_name == "projects":
                for proj in parsed.get("projects") or []:
                    if isinstance(proj, dict) and proj.get("bullets"):
                        bullets = proj["bullets"]
                        for i, b in enumerate(bullets):
                            if str(b).strip() == c.original_content.strip():
                                bullets[i] = active_text

        return parsed
