import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

NotificationTypeLiteral = Literal[
    "application_follow_up",
    "interview_reminder",
    "assessment_reminder",
    "application_deadline",
    "job_freshness_update",
    "task_completion",
    "system",
]


class NotificationResponse(BaseModel):
    """Notification response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    delivery_status: str
    idempotency_key: Optional[str] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""

    items: list[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class UnreadCountResponse(BaseModel):
    """Unread notification count response."""

    unread_count: int


class MarkReadAllResponse(BaseModel):
    """Mark all as read response."""

    updated_count: int


class UserNotificationPreferenceResponse(BaseModel):
    """User notification and reminder preference response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    enable_in_app: bool
    enable_interview_reminders: bool
    enable_assessment_reminders: bool
    enable_follow_up_reminders: bool
    enable_deadline_reminders: bool
    enable_job_freshness_updates: bool
    enable_task_completion_updates: bool
    enable_system_notifications: bool
    interview_reminder_24h: bool
    interview_reminder_1h: bool
    preferred_timezone: str
    created_at: datetime
    updated_at: datetime


class UserNotificationPreferenceUpdate(BaseModel):
    """User notification preference update schema."""

    enable_in_app: Optional[bool] = None
    enable_interview_reminders: Optional[bool] = None
    enable_assessment_reminders: Optional[bool] = None
    enable_follow_up_reminders: Optional[bool] = None
    enable_deadline_reminders: Optional[bool] = None
    enable_job_freshness_updates: Optional[bool] = None
    enable_task_completion_updates: Optional[bool] = None
    enable_system_notifications: Optional[bool] = None
    interview_reminder_24h: Optional[bool] = None
    interview_reminder_1h: Optional[bool] = None
    preferred_timezone: Optional[str] = None


class ProcessRemindersResponse(BaseModel):
    """Process reminders execution result."""

    reminders_created: int
    scanned_interviews: int = 0
    scanned_applications: int = 0
