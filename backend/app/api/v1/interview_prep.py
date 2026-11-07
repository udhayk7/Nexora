import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.interview_prep import (
    InterviewAnalyticsResponse,
    InterviewAnswerDetail,
    InterviewAnswerSubmitRequest,
    InterviewNoteCreateRequest,
    InterviewNoteResponse,
    InterviewNoteUpdateRequest,
    InterviewReminderCreateRequest,
    InterviewSessionCreateRequest,
    InterviewSessionDetail,
    InterviewSessionSummary,
    ProjectPreparationGenerateRequest,
    StructuredProjectBreakdown,
)
from app.schemas.notification import NotificationResponse
from app.services.interview_prep_service import InterviewPrepService

router = APIRouter(prefix="/interview-prep", tags=["AI Interview Preparation & Coaching"])


# ============================================================================
# Session Management & Mock Interview
# ============================================================================


@router.post(
    "/sessions",
    response_model=InterviewSessionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new personalized interview preparation session",
)
def create_interview_session(
    data: InterviewSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionDetail:
    """
    Generate grounded interview plan and role-specific questions for target job and candidate.
    """
    return InterviewPrepService.create_session(db=db, user=current_user, data=data)


@router.get(
    "/sessions",
    response_model=list[InterviewSessionSummary],
    summary="List interview preparation sessions",
)
def list_interview_sessions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterviewSessionSummary]:
    """Retrieve history of user's interview preparation sessions."""
    return InterviewPrepService.list_sessions(
        db=db, user=current_user, status=status_filter, limit=limit, offset=offset
    )


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionDetail,
    summary="Get interview session details with questions and evaluations",
)
def get_interview_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionDetail:
    """Retrieve complete session detail, questions, answers, and feedback."""
    return InterviewPrepService.get_session_detail(db=db, user=current_user, session_id=session_id)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=InterviewSessionDetail,
    summary="Mark interview preparation session as completed",
)
def complete_interview_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionDetail:
    """Explicitly mark session as completed."""
    return InterviewPrepService.complete_or_abandon_session(
        db=db, user=current_user, session_id=session_id, status="completed"
    )


@router.post(
    "/sessions/{session_id}/abandon",
    response_model=InterviewSessionDetail,
    summary="Abandon interview preparation session",
)
def abandon_interview_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionDetail:
    """Abandon an in-progress session."""
    return InterviewPrepService.complete_or_abandon_session(
        db=db, user=current_user, session_id=session_id, status="abandoned"
    )


@router.post(
    "/sessions/{session_id}/questions/{question_id}/answer",
    response_model=InterviewAnswerDetail,
    summary="Submit answer and receive multi-rubric evaluation",
)
def submit_interview_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    data: InterviewAnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewAnswerDetail:
    """
    Submit spoken/written answer and optional code. Evaluates answer statically against rubric.
    """
    return InterviewPrepService.submit_answer(
        db=db,
        user=current_user,
        session_id=session_id,
        question_id=question_id,
        data=data,
    )


# ============================================================================
# Project Deep-Dive Coaching
# ============================================================================


@router.post(
    "/projects/breakdown",
    response_model=StructuredProjectBreakdown,
    summary="Generate structured STAR breakdown for an evidenced resume project",
)
@router.post(
    "/project-breakdown",
    response_model=StructuredProjectBreakdown,
    include_in_schema=False,
)
def generate_project_breakdown(
    data: ProjectPreparationGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StructuredProjectBreakdown:
    """
    Generate pitch, architecture, trade-offs, and practice questions for an evidenced project.
    """
    return InterviewPrepService.generate_project_breakdown(db=db, user=current_user, data=data)


# ============================================================================
# Performance Analytics
# ============================================================================


@router.get(
    "/analytics",
    response_model=InterviewAnalyticsResponse,
    summary="Retrieve user interview performance analytics",
)
def get_interview_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewAnalyticsResponse:
    """
    Return performance dashboard metrics, category breakdown, score trends, and revision topics.
    """
    return InterviewPrepService.get_analytics(db=db, user=current_user)


# ============================================================================
# Preparation Notes & Checklists
# ============================================================================


@router.post(
    "/notes",
    response_model=InterviewNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an interview preparation note or checklist",
)
def create_interview_note(
    data: InterviewNoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewNoteResponse:
    """Save revision topics, questions to ask, company research, or checklist."""
    return InterviewPrepService.create_note(db=db, user=current_user, data=data)


@router.get(
    "/notes",
    response_model=list[InterviewNoteResponse],
    summary="List interview preparation notes",
)
def list_interview_notes(
    note_type: Optional[str] = Query(None),
    session_id: Optional[uuid.UUID] = Query(None),
    application_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterviewNoteResponse]:
    """Retrieve saved preparation notes and checklists."""
    return InterviewPrepService.list_notes(
        db=db,
        user=current_user,
        note_type=note_type,
        session_id=session_id,
        application_id=application_id,
    )


@router.patch(
    "/notes/{note_id}",
    response_model=InterviewNoteResponse,
    summary="Update an interview preparation note",
)
@router.put(
    "/notes/{note_id}",
    response_model=InterviewNoteResponse,
    include_in_schema=False,
)
def update_interview_note(
    note_id: uuid.UUID,
    data: InterviewNoteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewNoteResponse:
    """Edit title, content, checklist items, or pinned status."""
    return InterviewPrepService.update_note(db=db, user=current_user, note_id=note_id, data=data)


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview preparation note",
)
def delete_interview_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an interview note."""
    InterviewPrepService.delete_note(db=db, user=current_user, note_id=note_id)


# ============================================================================
# Interview Reminder
# ============================================================================


@router.post(
    "/reminders",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an interview reminder notification",
)
def create_interview_reminder(
    data: InterviewReminderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Schedule reminder before an upcoming interview using existing Notification infrastructure."""
    return InterviewPrepService.create_interview_reminder(db=db, user=current_user, data=data)
