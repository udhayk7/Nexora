import logging
from datetime import datetime, timezone

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.models.networking import NetworkingContact
from app.models.notification import Notification
from app.services.notification_service import NotificationService

logger = logging.getLogger("nexora.tasks.networking")


@celery.task(name="check_networking_followups_task")
def check_networking_followups_task() -> dict[str, int]:
    """Background task to detect due recruiter follow-ups and create non-duplicate alerts."""
    db = SessionLocal()
    notifications_sent = 0
    now = datetime.now(timezone.utc)

    try:
        due_contacts = (
            db.query(NetworkingContact)
            .filter(
                NetworkingContact.next_follow_up_date <= now,
                NetworkingContact.relationship_status.in_(
                    ("contacted", "awaiting_response", "follow_up_required")
                ),
            )
            .all()
        )

        for contact in due_contacts:
            rec = contact.recruiter
            if not rec:
                continue

            # Deduplication: check if notification already exists for this contact in the last 24h
            existing_notif = (
                db.query(Notification)
                .filter(
                    Notification.user_id == contact.user_id,
                    Notification.entity_type == "networking_contact",
                    Notification.entity_id == contact.id,
                )
                .first()
            )
            if existing_notif:
                continue

            # Create notification record
            NotificationService.create_notification_record(
                db=db,
                user_id=contact.user_id,
                notification_type="application_follow_up",
                title=f"Follow-up Due: {rec.full_name}",
                message=(
                    f"Follow-up scheduled with {rec.full_name} ({rec.company_name}). "
                    f"Review outreach draft in Networking CRM."
                ),
                entity_type="networking_contact",
                entity_id=contact.id,
                action_url="/dashboard/networking",
                idempotency_key=f"networking_followup_{contact.id}_{now.strftime('%Y%m%d')}",
            )
            notifications_sent += 1

        db.commit()
        return {"due_contacts_found": len(due_contacts), "notifications_sent": notifications_sent}
    except Exception as exc:
        logger.error("Error running check_networking_followups_task: %s", exc, exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
