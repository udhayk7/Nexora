import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationActivityCreate,
    ApplicationActivityResponse,
    ApplicationActivityUpdate,
    ApplicationAnalyticsResponse,
    ApplicationInterviewCreate,
    ApplicationInterviewResponse,
    ApplicationInterviewUpdate,
    JobApplicationCreate,
    JobApplicationDetailResponse,
    JobApplicationListResponse,
    JobApplicationStatusUpdate,
    JobApplicationUpdate,
)
from app.services.application_service import ApplicationService

applications_router = APIRouter(prefix="/applications", tags=["Application Management"])


@applications_router.post(
    "",
    response_model=JobApplicationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track a new job application",
)
def create_application(
    data: JobApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationDetailResponse:
    """Create a new job application tracking record for the authenticated user."""
    return ApplicationService.create_application(
        db=db,
        user_id=current_user.id,
        data=data,
    )


@applications_router.get(
    "/analytics",
    response_model=ApplicationAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve application pipeline analytics and upcoming events",
)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationAnalyticsResponse:
    """Compute application metrics, pipeline distribution, and upcoming deadlines from DB."""
    return ApplicationService.get_analytics(db=db, user_id=current_user.id)


@applications_router.get(
    "",
    response_model=JobApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter tracked job applications",
)
def list_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    channel: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at_desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationListResponse:
    """List applications for the current user with pagination, search, and filtering."""
    return ApplicationService.list_applications(
        db=db,
        user_id=current_user.id,
        status=status_filter,
        channel=channel,
        search=search,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )


@applications_router.get(
    "/{application_id}",
    response_model=JobApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve application details with timeline and interviews",
)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationDetailResponse:
    """Fetch complete detail, status transitions, activity timeline, and scheduled interviews."""
    return ApplicationService.get_application_detail(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
    )


@applications_router.patch(
    "/{application_id}",
    response_model=JobApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application details",
)
def update_application(
    application_id: uuid.UUID,
    data: JobApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationDetailResponse:
    """Update editable metadata, contact details, dates, or notes of an application."""
    return ApplicationService.update_application(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        data=data,
    )


@applications_router.patch(
    "/{application_id}/status",
    response_model=JobApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application stage status",
)
def update_status(
    application_id: uuid.UUID,
    data: JobApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationDetailResponse:
    """
    Transition application to a new pipeline status.
    Preserves audit history and appends to activity timeline.
    """
    return ApplicationService.update_status(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        data=data,
    )


@applications_router.post(
    "/{application_id}/link-opened",
    response_model=JobApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Record application link opened event",
)
def record_link_opened(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobApplicationDetailResponse:
    """
    Records that user navigated to the external application portal.
    Distinct from preparation or submission.
    """
    return ApplicationService.record_link_opened(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
    )


@applications_router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job application record",
)
def delete_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Delete an application and its timeline without affecting shared entities."""
    ApplicationService.delete_application(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Activities Endpoints ---


@applications_router.post(
    "/{application_id}/activities",
    response_model=ApplicationActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an activity or personal note",
)
def add_activity(
    application_id: uuid.UUID,
    data: ApplicationActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationActivityResponse:
    """Append a timeline event or note to the application."""
    return ApplicationService.add_activity(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        data=data,
    )


@applications_router.patch(
    "/{application_id}/activities/{activity_id}",
    response_model=ApplicationActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an activity or personal note",
)
def update_activity(
    application_id: uuid.UUID,
    activity_id: uuid.UUID,
    data: ApplicationActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationActivityResponse:
    """Update title, description, or date of an existing activity."""
    return ApplicationService.update_activity(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        activity_id=activity_id,
        data=data,
    )


@applications_router.delete(
    "/{application_id}/activities/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity or personal note",
)
def delete_activity(
    application_id: uuid.UUID,
    activity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Delete an activity from the timeline."""
    ApplicationService.delete_activity(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        activity_id=activity_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Interviews & Assessments Endpoints ---


@applications_router.post(
    "/{application_id}/interviews",
    response_model=ApplicationInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an interview or assessment",
)
def create_interview(
    application_id: uuid.UUID,
    data: ApplicationInterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationInterviewResponse:
    """Record an upcoming or completed interview round or assessment."""
    return ApplicationService.create_interview(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        data=data,
    )


@applications_router.patch(
    "/{application_id}/interviews/{interview_id}",
    response_model=ApplicationInterviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Update interview or assessment round",
)
def update_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    data: ApplicationInterviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ApplicationInterviewResponse:
    """Update meeting URL, notes, outcome, or completion status of an interview."""
    return ApplicationService.update_interview(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        interview_id=interview_id,
        data=data,
    )


@applications_router.delete(
    "/{application_id}/interviews/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview or assessment round",
)
def delete_interview(
    application_id: uuid.UUID,
    interview_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Delete an interview / assessment round."""
    ApplicationService.delete_interview(
        db=db,
        user_id=current_user.id,
        application_id=application_id,
        interview_id=interview_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
