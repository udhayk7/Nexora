import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.audit import audit_service
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.core.storage import storage_service
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import (
    AnalyzeResumeRequest,
    ResumeAnalysisDetail,
    ResumeAnalysisStatusResponse,
    ResumeAnalysisSummary,
)
from app.schemas.resume import (
    ResumeDetailResponse,
    ResumeSummaryResponse,
    ResumeVersionDetail,
    ResumeVersionSummary,
)
from app.services.ai.analyzer import analysis_service
from app.services.resume_parser import resume_parser

resumes_router = APIRouter(prefix="/resumes", tags=["resumes"])


def _validate_and_extract_type(filename: str, content: bytes) -> str:
    """Validate file extension and magic byte signature."""
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise BadRequestError(f"File size exceeds maximum allowed limit of {max_mb:.0f}MB")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise BadRequestError(
            f"Unsupported file type '{ext}'. Only .pdf and .docx files are permitted."
        )

    if ext == ".pdf":
        if not content.startswith(b"%PDF"):
            raise BadRequestError("File content does not match standard PDF header.")
        return "pdf"
    elif ext == ".docx":
        # ZIP magic signature used by OpenXML (.docx)
        if not (content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06")):
            raise BadRequestError("File content does not match standard DOCX format.")
        return "docx"

    raise BadRequestError("Unsupported file format.")


def _get_media_type(file_type: str) -> str:
    if "pdf" in file_type.lower():
        return "application/pdf"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _format_detail_response(resume: Resume) -> ResumeDetailResponse:
    # Sort versions descending by version_number
    versions_sorted = sorted(resume.versions, key=lambda v: v.version_number, reverse=True)

    current_ver: Optional[ResumeVersionDetail] = None
    if resume.current_version_id:
        target_v = next((v for v in versions_sorted if v.id == resume.current_version_id), None)
        if target_v:
            current_ver = ResumeVersionDetail.model_validate(target_v)

    if not current_ver and versions_sorted:
        current_ver = ResumeVersionDetail.model_validate(versions_sorted[0])

    version_summaries = [ResumeVersionSummary.model_validate(v) for v in versions_sorted]

    return ResumeDetailResponse(
        id=resume.id,
        title=resume.title,
        current_version_id=resume.current_version_id,
        current_version=current_ver,
        versions=version_summaries,
        version_count=len(versions_sorted),
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


@resumes_router.post(
    "",
    response_model=ResumeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a new resume",
)
async def upload_resume(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    """Upload PDF/DOCX, extract text, persist file, and parse structured sections."""
    original_filename = file.filename or "resume.pdf"
    content = await file.read()

    file_type = _validate_and_extract_type(original_filename, content)

    # Derive default title if not provided
    default_title = os.path.splitext(original_filename)[0]
    resolved_title = title.strip() if title and title.strip() else default_title
    if len(resolved_title) > 255:
        resolved_title = resolved_title[:255]

    resume_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Store file safely
    storage_path = storage_service.save_file(
        user_id=current_user.id,
        resume_id=resume_id,
        version_id=version_id,
        filename=original_filename,
        content=content,
    )

    # Deterministic parsing
    raw_text, parsed_data, parsing_status, error_summary = resume_parser.parse_document(
        content=content,
        file_type=file_type,
    )

    resume = Resume(
        id=resume_id,
        user_id=current_user.id,
        title=resolved_title,
        current_version_id=version_id,
    )
    db.add(resume)
    db.flush()

    version = ResumeVersion(
        id=version_id,
        resume_id=resume.id,
        version_number=1,
        original_filename=original_filename,
        file_type=file_type,
        file_size=len(content),
        storage_path=storage_path,
        parsing_status=parsing_status,
        parsed_content=parsed_data if parsing_status == "parsed" else None,
        raw_text=raw_text if parsing_status == "parsed" else None,
        error_summary=error_summary,
    )
    db.add(version)
    db.commit()
    db.refresh(resume)

    audit_service.record_event(
        action="resume.upload",
        resource_type="resume",
        actor_type="user",
        actor_id=str(current_user.id),
        resource_id=str(resume.id),
        metadata={
            "filename": original_filename,
            "file_size": len(content),
            "file_type": file_type,
            "version_number": 1,
        },
    )

    audit_service.record_event(
        action="resume.parsed",
        resource_type="resume_version",
        actor_type="user",
        actor_id=str(current_user.id),
        resource_id=str(version.id),
        metadata={
            "status": parsing_status,
            "skills_count": len(parsed_data.get("skills", [])),
            "experience_count": len(parsed_data.get("experience", [])),
        },
    )

    logger.info(
        f"Uploaded and parsed resume {resume.id} v1 for user {current_user.id} "
        f"(status: {parsing_status})"
    )

    return _format_detail_response(resume)


@resumes_router.get(
    "",
    response_model=list[ResumeSummaryResponse],
    summary="List all resumes for the authenticated user",
)
def list_resumes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[ResumeSummaryResponse]:
    """Retrieve all resumes owned by the current active user."""
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.updated_at.desc())
        .all()
    )

    summaries: list[ResumeSummaryResponse] = []
    for r in resumes:
        versions = sorted(r.versions, key=lambda v: v.version_number, reverse=True)
        active_v = next((v for v in versions if v.id == r.current_version_id), None)
        if not active_v and versions:
            active_v = versions[0]

        summaries.append(
            ResumeSummaryResponse(
                id=r.id,
                title=r.title,
                current_version_id=r.current_version_id,
                current_version_number=active_v.version_number if active_v else None,
                parsing_status=active_v.parsing_status if active_v else "uploaded",
                original_filename=active_v.original_filename if active_v else None,
                file_type=active_v.file_type if active_v else None,
                file_size=active_v.file_size if active_v else None,
                version_count=len(versions),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return summaries


@resumes_router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Retrieve resume details and parsed profile",
)
def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeDetailResponse:
    """Retrieve full resume details with structured profile and version list."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise NotFoundError("Resume not found")

    return _format_detail_response(resume)


@resumes_router.post(
    "/{resume_id}/versions",
    response_model=ResumeVersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new version of an existing resume",
)
async def upload_resume_version(
    resume_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeVersionDetail:
    """Upload and parse a new version for an existing resume record."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise NotFoundError("Resume not found")

    original_filename = file.filename or "resume.pdf"
    content = await file.read()
    file_type = _validate_and_extract_type(original_filename, content)

    next_version_num = (
        max((v.version_number for v in resume.versions), default=0) + 1
    )
    version_id = uuid.uuid4()

    storage_path = storage_service.save_file(
        user_id=current_user.id,
        resume_id=resume.id,
        version_id=version_id,
        filename=original_filename,
        content=content,
    )

    raw_text, parsed_data, parsing_status, error_summary = resume_parser.parse_document(
        content=content,
        file_type=file_type,
    )

    version = ResumeVersion(
        id=version_id,
        resume_id=resume.id,
        version_number=next_version_num,
        original_filename=original_filename,
        file_type=file_type,
        file_size=len(content),
        storage_path=storage_path,
        parsing_status=parsing_status,
        parsed_content=parsed_data if parsing_status == "parsed" else None,
        raw_text=raw_text if parsing_status == "parsed" else None,
        error_summary=error_summary,
    )
    db.add(version)

    resume.current_version_id = version.id
    db.commit()
    db.refresh(version)

    audit_service.record_event(
        action="resume.upload_version",
        resource_type="resume",
        actor_type="user",
        actor_id=str(current_user.id),
        resource_id=str(resume.id),
        metadata={
            "version_id": str(version.id),
            "version_number": next_version_num,
            "filename": original_filename,
            "file_size": len(content),
        },
    )

    return ResumeVersionDetail.model_validate(version)


@resumes_router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeVersionSummary],
    summary="List version history for a resume",
)
def list_resume_versions(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[ResumeVersionSummary]:
    """List all versions of a specific resume."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise NotFoundError("Resume not found")

    versions = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume.id)
        .order_by(ResumeVersion.version_number.desc())
        .all()
    )
    return [ResumeVersionSummary.model_validate(v) for v in versions]


@resumes_router.get(
    "/{resume_id}/versions/{version_id}",
    response_model=ResumeVersionDetail,
    summary="Retrieve a specific version of a resume",
)
def get_resume_version(
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeVersionDetail:
    """Retrieve details and parsed content of a specific resume version."""
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

    return ResumeVersionDetail.model_validate(version)


@resumes_router.get(
    "/{resume_id}/download",
    summary="Download original file for active resume version",
)
def download_resume(
    resume_id: uuid.UUID,
    version_id: Optional[uuid.UUID] = Query(None, description="Optional version to download"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the original source document for a resume or specific version."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise NotFoundError("Resume not found")

    target_version_id = version_id or resume.current_version_id
    version: Optional[ResumeVersion] = None
    if not target_version_id:
        version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume.id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )
        if not version:
            raise NotFoundError("No versions found for this resume")
    else:
        version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.id == target_version_id, ResumeVersion.resume_id == resume.id)
            .first()
        )
        if not version:
            raise NotFoundError("Resume version not found")

    try:
        file_bytes = storage_service.get_file(version.storage_path)
    except FileNotFoundError:
        raise NotFoundError("Stored file not found on disk") from None

    audit_service.record_event(
        action="resume.download",
        resource_type="resume_version",
        actor_type="user",
        actor_id=str(current_user.id),
        resource_id=str(version.id),
        metadata={
            "resume_id": str(resume.id),
            "version_number": version.version_number,
            "filename": version.original_filename,
        },
    )

    # Encode safe Content-Disposition header
    safe_name = version.original_filename.replace('"', '\\"')
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "Content-Length": str(len(file_bytes)),
    }

    return Response(
        content=file_bytes,
        media_type=_get_media_type(version.file_type),
        headers=headers,
    )


@resumes_router.get(
    "/{resume_id}/versions/{version_id}/download",
    summary="Download original file for a specific resume version",
)
def download_resume_version(
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download specific version file."""
    return download_resume(
        resume_id=resume_id,
        version_id=version_id,
        current_user=current_user,
        db=db,
    )


@resumes_router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume and all its versions",
)
def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a resume, all its versions from database, and remove stored files."""
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise NotFoundError("Resume not found")

    # Clean up files on disk
    storage_service.delete_resume_directory(current_user.id, resume.id)

    db.delete(resume)
    db.commit()

    audit_service.record_event(
        action="resume.delete",
        resource_type="resume",
        actor_type="user",
        actor_id=str(current_user.id),
        resource_id=str(resume_id),
        metadata={},
    )

    logger.info(f"Deleted resume {resume_id} and storage files for user {current_user.id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- AI Resume Intelligence Endpoints ---


@resumes_router.post(
    "/{resume_id}/versions/{version_id}/analysis",
    response_model=ResumeAnalysisDetail,
    status_code=status.HTTP_200_OK,
    summary="Trigger evidence-grounded AI intelligence analysis for a resume version",
)
def request_resume_analysis(
    resume_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: Optional[AnalyzeResumeRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeAnalysisDetail:
    """Analyze a resume version using configured AI provider with strict evidence grounding."""
    force = payload.force_refresh if payload else False
    analysis = analysis_service.analyze_version(
        db=db,
        current_user=current_user,
        resume_id=resume_id,
        version_id=version_id,
        force_refresh=force,
    )
    return ResumeAnalysisDetail.model_validate(analysis)


@resumes_router.get(
    "/{resume_id}/analysis",
    response_model=list[ResumeAnalysisSummary],
    summary="List analysis history for a resume",
)
def list_resume_analyses(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[ResumeAnalysisSummary]:
    """Retrieve history of AI analyses performed on this resume."""
    analyses = analysis_service.list_analyses(
        db=db,
        current_user=current_user,
        resume_id=resume_id,
    )

    summaries: list[ResumeAnalysisSummary] = []
    for a in analyses:
        career_lvl = None
        domains: list[str] = []
        if a.result and isinstance(a.result, dict):
            profile = a.result.get("profile", {})
            career_lvl = profile.get("career_level_estimate")
            domains = profile.get("domains", [])

        summaries.append(
            ResumeAnalysisSummary(
                id=a.id,
                resume_id=a.resume_id,
                version_id=a.version_id,
                status=a.status,
                provider=a.provider,
                model=a.model,
                career_level=career_lvl,
                top_domains=domains,
                created_at=a.created_at,
                completed_at=a.completed_at,
            )
        )
    return summaries


@resumes_router.get(
    "/{resume_id}/analysis/{analysis_id}",
    response_model=ResumeAnalysisDetail,
    summary="Retrieve full results of a specific AI analysis",
)
def get_resume_analysis(
    resume_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeAnalysisDetail:
    """Retrieve full structured analysis result including evidence citations."""
    analysis = analysis_service.get_analysis(
        db=db,
        current_user=current_user,
        resume_id=resume_id,
        analysis_id=analysis_id,
    )
    return ResumeAnalysisDetail.model_validate(analysis)


@resumes_router.get(
    "/{resume_id}/analysis/{analysis_id}/status",
    response_model=ResumeAnalysisStatusResponse,
    summary="Retrieve execution status of a specific AI analysis",
)
def get_resume_analysis_status(
    resume_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ResumeAnalysisStatusResponse:
    """Retrieve execution status of an analysis."""
    analysis = analysis_service.get_analysis(
        db=db,
        current_user=current_user,
        resume_id=resume_id,
        analysis_id=analysis_id,
    )
    return ResumeAnalysisStatusResponse.model_validate(analysis)

