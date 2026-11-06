import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.tailoring import (
    BatchChangeActionRequest,
    ChangeStatusUpdateRequest,
    CompilePDFRequest,
    CompilePDFResponse,
    SaveTailoredVersionRequest,
    TailoredVersionResponse,
    TailoringSessionCreateRequest,
    TailoringSessionResponse,
    TailoringSessionSummaryResponse,
    UpdateContentRequest,
)
from app.services.tailoring_service import TailoringService

tailoring_router = APIRouter(prefix="/tailoring", tags=["Resume Tailoring Studio"])


@tailoring_router.post(
    "/sessions",
    response_model=TailoringSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a job-specific resume tailoring session",
)
def create_session(
    req: TailoringSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoringSessionResponse:
    """
    Initializes a new tailoring session comparing candidate resume evidence against
    target job requirements, extracting grounded modifications, and generating initial LaTeX.
    """
    return TailoringService.create_session(db=db, user_id=current_user.id, req=req)


@tailoring_router.get(
    "/sessions",
    response_model=list[TailoringSessionSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List past tailoring sessions for the current user",
)
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TailoringSessionSummaryResponse]:
    """Retrieve history of tailoring sessions for candidate's resumes."""
    return TailoringService.list_user_sessions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@tailoring_router.get(
    "/sessions/{session_id}",
    response_model=TailoringSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve tailoring session state and changes",
)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoringSessionResponse:
    """Fetch complete tailoring workspace including job, alignment analysis, changes, and LaTeX."""
    return TailoringService.get_session(db=db, session_id=session_id, user_id=current_user.id)


@tailoring_router.patch(
    "/sessions/{session_id}/changes/{change_id}",
    response_model=TailoringSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update change approval status or provide custom text",
)
def update_change_status(
    session_id: uuid.UUID,
    change_id: uuid.UUID,
    req: ChangeStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoringSessionResponse:
    """
    Accept, reject, or manually customize an individual proposed modification.
    Automatically keeps active LaTeX in sync with approved modifications.
    """
    return TailoringService.update_change_status(
        db=db,
        session_id=session_id,
        change_id=change_id,
        user_id=current_user.id,
        req=req,
    )


@tailoring_router.post(
    "/sessions/{session_id}/batch",
    response_model=TailoringSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch approve or restore original content",
)
def batch_update_changes(
    session_id: uuid.UUID,
    req: BatchChangeActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoringSessionResponse:
    """Perform batch actions across all proposed modifications."""
    return TailoringService.batch_update_changes(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        req=req,
    )


@tailoring_router.put(
    "/sessions/{session_id}/content",
    response_model=TailoringSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Save user LaTeX edits from Monaco editor",
)
def update_content(
    session_id: uuid.UUID,
    req: UpdateContentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoringSessionResponse:
    """Directly save LaTeX document modifications edited in the code editor."""
    return TailoringService.update_latex_content(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        req=req,
    )


@tailoring_router.post(
    "/sessions/{session_id}/compile",
    response_model=CompilePDFResponse,
    status_code=status.HTTP_200_OK,
    summary="Compile active LaTeX document into sandboxed PDF",
)
def compile_pdf(
    session_id: uuid.UUID,
    req: Optional[CompilePDFRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompilePDFResponse:
    """
    Runs sandboxed compilation on the session's active LaTeX document.
    Disallows shell escape and commands.
    """
    latex_text = req.latex_content if req else None
    _, resp = TailoringService.compile_pdf(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        latex_content=latex_text,
    )
    return resp


@tailoring_router.get(
    "/sessions/{session_id}/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download or stream compiled PDF preview",
)
def download_pdf(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Compile and stream the active PDF document for in-browser rendering."""
    pdf_bytes, _ = TailoringService.compile_pdf(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="tailored_resume_{session_id}.pdf"',
            "Content-Type": "application/pdf",
        },
    )


@tailoring_router.get(
    "/sessions/{session_id}/latex",
    status_code=status.HTTP_200_OK,
    summary="Download raw LaTeX source code",
)
def download_latex(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Download the active LaTeX source file."""
    session = TailoringService.get_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    latex_content = session.latex_content or ""
    return Response(
        content=latex_content,
        media_type="text/x-tex; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="tailored_resume_{session_id}.tex"',
            "Content-Type": "text/x-tex; charset=utf-8",
        },
    )


@tailoring_router.post(
    "/sessions/{session_id}/save",
    response_model=TailoredVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save tailored resume as a new immutable ResumeVersion",
)
def save_tailored_version(
    session_id: uuid.UUID,
    req: SaveTailoredVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TailoredVersionResponse:
    """
    Persists tailored resume into an immutable ResumeVersion.
    Preserves parent version history and original resume integrity.
    """
    version = TailoringService.save_tailored_version(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        req=req,
    )
    return TailoredVersionResponse.model_validate(version)

