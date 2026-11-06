import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.models.application import ApplicationInterview, JobApplication
from app.models.notification import Notification, UserNotificationPreference
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    ProcessRemindersResponse,
    UnreadCountResponse,
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to convert any datetime (naive or aware) to UTC-aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class NotificationService:
    """Service managing user notifications, preferences, and automated reminder generation."""

    @classmethod
    def get_or_create_preferences(
        cls, db: Session, user_id: uuid.UUID
    ) -> UserNotificationPreference:
        """Fetch user notification preferences or instantiate default preferences if not yet set."""
        pref = (
            db.query(UserNotificationPreference)
            .filter(UserNotificationPreference.user_id == user_id)
            .first()
        )
        if not pref:
            pref = UserNotificationPreference(
                user_id=user_id,
                enable_in_app=True,
                enable_interview_reminders=True,
                enable_assessment_reminders=True,
                enable_follow_up_reminders=True,
                enable_deadline_reminders=True,
                enable_job_freshness_updates=True,
                enable_task_completion_updates=True,
                enable_system_notifications=True,
                interview_reminder_24h=True,
                interview_reminder_1h=True,
                preferred_timezone="UTC",
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @classmethod
    def update_preferences(
        cls, db: Session, user_id: uuid.UUID, data: UserNotificationPreferenceUpdate
    ) -> UserNotificationPreferenceResponse:
        """Update notification preferences for the authenticated user."""
        pref = cls.get_or_create_preferences(db, user_id)

        update_dict = data.model_dump(exclude_unset=True)

        # Validate timezone if requested
        if "preferred_timezone" in update_dict and update_dict["preferred_timezone"]:
            tz_str = update_dict["preferred_timezone"].strip()
            try:
                ZoneInfo(tz_str)
                update_dict["preferred_timezone"] = tz_str
            except (ZoneInfoNotFoundError, KeyError, ValueError) as err:
                raise BadRequestError(
                    f"Invalid IANA timezone '{tz_str}'. "
                    "Example valid timezones: 'UTC', 'America/New_York', 'Asia/Kolkata'."
                ) from err

        for field, value in update_dict.items():
            setattr(pref, field, value)

        db.commit()
        db.refresh(pref)

        audit_service.record_event(
            action="notification.preferences_updated",
            actor_type="user",
            actor_id=str(user_id),
            resource_type="user_notification_preferences",
            resource_id=str(pref.id),
            metadata={"preferred_timezone": pref.preferred_timezone},
        )

        return UserNotificationPreferenceResponse.model_validate(pref)

    @classmethod
    def create_notification_record(
        cls,
        db: Session,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        action_url: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        delivery_status: str = "delivered",
        idempotency_key: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> tuple[Optional[Notification], bool]:
        """
        Create a persistent notification entity after verifying category preferences
        and enforcing strict idempotency deduplication.
        Returns a tuple of (Notification, was_created).
        """
        # 1. Check user preferences
        pref = cls.get_or_create_preferences(db, user_id)
        if not pref.enable_in_app:
            return None, False

        # Category checks
        if notification_type == "interview_reminder" and not pref.enable_interview_reminders:
            return None, False
        if notification_type == "assessment_reminder" and not pref.enable_assessment_reminders:
            return None, False
        if notification_type == "application_deadline" and not pref.enable_deadline_reminders:
            return None, False
        if notification_type == "application_follow_up" and not pref.enable_follow_up_reminders:
            return None, False
        if notification_type == "job_freshness_update" and not pref.enable_job_freshness_updates:
            return None, False
        if (
            notification_type == "task_completion"
            and not pref.enable_task_completion_updates
        ):
            return None, False
        if notification_type == "system" and not pref.enable_system_notifications:
            return None, False

        # 2. Check existing idempotency key
        if idempotency_key:
            existing = (
                db.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing:
                return existing, False

        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            is_read=False,
            scheduled_for=_ensure_utc(scheduled_for),
            delivery_status=delivery_status,
            idempotency_key=idempotency_key,
            metadata_json=metadata_json or {},
        )

        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
        except IntegrityError:
            db.rollback()
            # If concurrent worker inserted with same idempotency key, return that record
            if idempotency_key:
                found = (
                    db.query(Notification)
                    .filter(
                        Notification.user_id == user_id,
                        Notification.idempotency_key == idempotency_key,
                    )
                    .first()
                )
                if found:
                    return found, False
            raise

        audit_service.record_event(
            action="notification.created",
            actor_type="user",
            actor_id=str(user_id),
            resource_type="notifications",
            resource_id=str(notification.id),
            metadata={
                "notification_type": notification_type,
                "entity_type": entity_type,
                "idempotency_key": idempotency_key,
            },
        )

        return notification, True

    @classmethod
    def create_notification(
        cls,
        db: Session,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        action_url: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
        delivery_status: str = "delivered",
        idempotency_key: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> Optional[Notification]:
        """Convenience method returning created or existing notification."""
        notif, _ = cls.create_notification_record(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            scheduled_for=scheduled_for,
            delivery_status=delivery_status,
            idempotency_key=idempotency_key,
            metadata_json=metadata_json,
        )
        return notif

    @classmethod
    def list_notifications(
        cls,
        db: Session,
        user_id: uuid.UUID,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> NotificationListResponse:
        """List user-scoped notifications with pagination, type filtering and unread count."""
        query = db.query(Notification).filter(Notification.user_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read.is_(False))

        if notification_type and notification_type != "all":
            query = query.filter(Notification.notification_type == notification_type)

        total = query.count()
        unread_count = (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )

        items = (
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in items],
            total=total,
            unread_count=unread_count,
            skip=skip,
            limit=limit,
        )

    @classmethod
    def get_unread_count(cls, db: Session, user_id: uuid.UUID) -> UnreadCountResponse:
        """Retrieve count of unread notifications for the user."""
        count = (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .scalar()
            or 0
        )
        return UnreadCountResponse(unread_count=count)

    @classmethod
    def mark_as_read(
        cls, db: Session, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> NotificationResponse:
        """Mark a single notification as read."""
        notification = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
        if not notification:
            raise NotFoundError("Notification not found")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notification)

            audit_service.record_event(
                action="notification.read",
                actor_type="user",
                actor_id=str(user_id),
                resource_type="notifications",
                resource_id=str(notification.id),
            )

        return NotificationResponse.model_validate(notification)

    @classmethod
    def mark_all_as_read(cls, db: Session, user_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for current user."""
        now = datetime.now(timezone.utc)
        result = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .update(
                {Notification.is_read: True, Notification.read_at: now},
                synchronize_session="fetch",
            )
        )
        db.commit()

        audit_service.record_event(
            action="notification.read_all",
            actor_type="user",
            actor_id=str(user_id),
            resource_type="notifications",
            metadata={"updated_count": result},
        )

        return result

    @classmethod
    def delete_notification(
        cls, db: Session, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> None:
        """Delete a notification belonging to the current user."""
        notification = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
        if not notification:
            raise NotFoundError("Notification not found")

        db.delete(notification)
        db.commit()

        audit_service.record_event(
            action="notification.deleted",
            actor_type="user",
            actor_id=str(user_id),
            resource_type="notifications",
            resource_id=str(notification_id),
        )

    @classmethod
    def process_reminders(
        cls, db: Session, target_user_id: Optional[uuid.UUID] = None
    ) -> ProcessRemindersResponse:
        """
        Scan upcoming interviews, assessments, deadlines, and follow-ups.
        Creates persistent, deduplicated notification records using exact intervals
        and timezone-aware conversions.
        """
        now = datetime.now(timezone.utc)
        created_count = 0
        scanned_interviews = 0
        scanned_applications = 0

        # Cache preferences per user_id during batch scan
        user_prefs_cache: dict[uuid.UUID, UserNotificationPreference] = {}

        def get_pref(uid: uuid.UUID) -> UserNotificationPreference:
            if uid not in user_prefs_cache:
                user_prefs_cache[uid] = cls.get_or_create_preferences(db, uid)
            return user_prefs_cache[uid]

        # ---------------------------------------------------------------------
        # 1. Interviews & Assessments (24h and 1h intervals)
        # ---------------------------------------------------------------------
        # Exclude cancelled, completed, or already decided rounds
        iv_query = db.query(ApplicationInterview).filter(
            ApplicationInterview.status == "scheduled",
            (ApplicationInterview.outcome.is_(None) | (ApplicationInterview.outcome == "pending")),
        )
        if target_user_id:
            iv_query = iv_query.filter(ApplicationInterview.user_id == target_user_id)

        interviews = iv_query.all()
        scanned_interviews = len(interviews)

        for iv in interviews:
            scheduled_utc = _ensure_utc(iv.scheduled_at)
            if not scheduled_utc or scheduled_utc <= now:
                # Event already started or in past; do not send reminders
                continue

            delta = scheduled_utc - now

            pref = get_pref(iv.user_id)
            if not pref.enable_in_app:
                continue

            is_assessment = (
                "assessment" in iv.interview_type
                or iv.interview_type in ("coding_assessment", "take_home", "online_assessment")
            )
            notif_type = "assessment_reminder" if is_assessment else "interview_reminder"
            category_enabled = (
                pref.enable_assessment_reminders
                if is_assessment
                else pref.enable_interview_reminders
            )
            if not category_enabled:
                continue

            # Timezone-aware formatted time
            try:
                user_tz = ZoneInfo(pref.preferred_timezone or "UTC")
            except Exception:
                user_tz = ZoneInfo("UTC")

            local_dt = scheduled_utc.astimezone(user_tz)
            time_display = local_dt.strftime("%b %d, %Y at %I:%M %p")
            type_label = "Assessment" if is_assessment else "Interview"

            # Window 1: 24-hour reminder (~24 hours prior)
            # Nominal window [23h45m, 24h15m] with 2-hour missed recovery grace period [22h, 24h15m]
            # An event 30 minutes away (< 22h) will NEVER trigger this 24-hour reminder
            within_24h = timedelta(hours=22) <= delta <= timedelta(hours=24, minutes=15)
            if pref.interview_reminder_24h and within_24h:
                idemp_24h = f"reminder:{notif_type}:24h:{iv.id}"
                _, was_created = cls.create_notification_record(
                    db=db,
                    user_id=iv.user_id,
                    notification_type=notif_type,
                    title=f"Upcoming {type_label}: Round {iv.round_number}",
                    message=(
                        f"Your {iv.title} is scheduled for {time_display} "
                        f"({pref.preferred_timezone})."
                    ),
                    entity_type="interview",
                    entity_id=iv.id,
                    action_url=iv.meeting_url or "/dashboard/applications",
                    scheduled_for=scheduled_utc,
                    idempotency_key=idemp_24h,
                    metadata_json={
                        "interval": "24h",
                        "round_number": iv.round_number,
                        "meeting_url": iv.meeting_url,
                    },
                )
                if was_created:
                    created_count += 1

            # Window 2: 1-hour reminder (~1 hour prior)
            # Nominal window [45m, 75m] with grace period down to event start (0 < delta <= 75m)
            # Will not send if event has already started
            within_1h = timedelta(0) < delta <= timedelta(hours=1, minutes=15)
            if pref.interview_reminder_1h and within_1h:
                idemp_1h = f"reminder:{notif_type}:1h:{iv.id}"
                _, was_created_1h = cls.create_notification_record(
                    db=db,
                    user_id=iv.user_id,
                    notification_type=notif_type,
                    title=f"Starting Soon: {iv.title}",
                    message=(
                        f"Your {type_label} starts in less than an hour at {time_display} "
                        f"({pref.preferred_timezone})."
                    ),
                    entity_type="interview",
                    entity_id=iv.id,
                    action_url=iv.meeting_url or "/dashboard/applications",
                    scheduled_for=scheduled_utc,
                    idempotency_key=idemp_1h,
                    metadata_json={
                        "interval": "1h",
                        "round_number": iv.round_number,
                        "meeting_url": iv.meeting_url,
                    },
                )
                if was_created_1h:
                    created_count += 1

        # ---------------------------------------------------------------------
        # 2. Application Deadlines & Follow-ups (Due date window)
        # ---------------------------------------------------------------------
        # Exclude rejected, withdrawn, or inactive applications
        app_query = db.query(JobApplication).filter(
            JobApplication.status.notin_(["rejected", "withdrawn"])
        )
        if target_user_id:
            app_query = app_query.filter(JobApplication.user_id == target_user_id)

        applications = app_query.all()
        scanned_applications = len(applications)

        for app in applications:
            pref = get_pref(app.user_id)
            if not pref.enable_in_app:
                continue

            try:
                user_tz = ZoneInfo(pref.preferred_timezone or "UTC")
            except Exception:
                user_tz = ZoneInfo("UTC")

            # Check Deadline
            if app.deadline_at and pref.enable_deadline_reminders:
                deadline_utc = _ensure_utc(app.deadline_at)
                # If deadline is within next 24 hours (or due today)
                if deadline_utc and now <= deadline_utc <= now + timedelta(hours=24, minutes=15):
                    local_deadline = deadline_utc.astimezone(user_tz)
                    date_key = local_deadline.strftime("%Y-%m-%d")
                    idemp_dl = f"reminder:deadline:{app.id}:{date_key}"
                    _, was_created_dl = cls.create_notification_record(
                        db=db,
                        user_id=app.user_id,
                        notification_type="application_deadline",
                        title=f"Application Deadline: {app.title}",
                        message=(
                            f"The submission deadline for {app.title} at {app.company_name} "
                            f"is on {local_deadline.strftime('%b %d, %Y')}."
                        ),
                        entity_type="application",
                        entity_id=app.id,
                        action_url="/dashboard/applications",
                        scheduled_for=deadline_utc,
                        idempotency_key=idemp_dl,
                        metadata_json={
                            "company_name": app.company_name,
                            "deadline": deadline_utc.isoformat(),
                        },
                    )
                    if was_created_dl:
                        created_count += 1

            # Check Next Follow-up
            if app.next_follow_up_at and pref.enable_follow_up_reminders:
                followup_utc = _ensure_utc(app.next_follow_up_at)
                # If follow-up date is within next 24 hours
                if followup_utc and now <= followup_utc <= now + timedelta(hours=24, minutes=15):
                    local_fu = followup_utc.astimezone(user_tz)
                    date_key = local_fu.strftime("%Y-%m-%d")
                    idemp_fu = f"reminder:follow_up:{app.id}:{date_key}"
                    _, was_created_fu = cls.create_notification_record(
                        db=db,
                        user_id=app.user_id,
                        notification_type="application_follow_up",
                        title=f"Follow-Up Due: {app.company_name}",
                        message=(
                            f"You scheduled a follow-up for your {app.title} application "
                            f"at {app.company_name} on {local_fu.strftime('%b %d, %Y')}."
                        ),
                        entity_type="application",
                        entity_id=app.id,
                        action_url="/dashboard/applications",
                        scheduled_for=followup_utc,
                        idempotency_key=idemp_fu,
                        metadata_json={
                            "company_name": app.company_name,
                            "follow_up": followup_utc.isoformat(),
                        },
                    )
                    if was_created_fu:
                        created_count += 1

        return ProcessRemindersResponse(
            reminders_created=created_count,
            scanned_interviews=scanned_interviews,
            scanned_applications=scanned_applications,
        )
