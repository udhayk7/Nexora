import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkReadAllResponse,
    NotificationListResponse,
    NotificationResponse,
    ProcessRemindersResponse,
    UnreadCountResponse,
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    notification_type: Optional[str] = Query(None, description="Filter by category type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    """List paginated notifications for the current authenticated user."""
    return NotificationService.list_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        skip=skip,
        limit=limit,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    """Retrieve the count of unread notifications for the active user session."""
    return NotificationService.get_unread_count(db=db, user_id=current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a specific notification as read."""
    return NotificationService.mark_as_read(
        db=db, user_id=current_user.id, notification_id=notification_id
    )


@router.post("/read-all", response_model=MarkReadAllResponse)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkReadAllResponse:
    """Mark all unread notifications as read for the authenticated user."""
    count = NotificationService.mark_all_as_read(db=db, user_id=current_user.id)
    return MarkReadAllResponse(updated_count=count)


@router.delete("/{notification_id}", status_code=status.HTTP_200_OK)
def delete_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a user-scoped notification."""
    NotificationService.delete_notification(
        db=db, user_id=current_user.id, notification_id=notification_id
    )
    return {"message": "Notification deleted successfully"}


@router.get("/preferences", response_model=UserNotificationPreferenceResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserNotificationPreferenceResponse:
    """Retrieve notification and reminder preferences for the authenticated user."""
    pref = NotificationService.get_or_create_preferences(db=db, user_id=current_user.id)
    return UserNotificationPreferenceResponse.model_validate(pref)


@router.put("/preferences", response_model=UserNotificationPreferenceResponse)
@router.patch("/preferences", response_model=UserNotificationPreferenceResponse)
def update_notification_preferences(
    data: UserNotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserNotificationPreferenceResponse:
    """Update notification preferences, intervals, categories, and timezone."""
    return NotificationService.update_preferences(
        db=db, user_id=current_user.id, data=data
    )


@router.post("/process-reminders", response_model=ProcessRemindersResponse)
def trigger_process_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProcessRemindersResponse:
    """
    On-demand trigger to scan and evaluate scheduled reminders for upcoming
    interviews, assessments, deadlines, and follow-ups.
    """
    return NotificationService.process_reminders(
        db=db, target_user_id=current_user.id
    )
