"""Celery background tasks for scheduled reminders and notifications."""

import logging
from typing import Any

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.services.notification_service import NotificationService

logger = logging.getLogger("nexora.tasks.reminders")


@celery.task(
    name="process_scheduled_reminders_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_scheduled_reminders_task(self: Any) -> dict[str, Any]:
    """
    Periodic or on-demand task that evaluates upcoming deadlines, follow-ups,
    and interview rounds, creating deduplicated notification records.
    """
    logger.info("Executing process_scheduled_reminders_task")
    db = SessionLocal()
    try:
        result = NotificationService.process_reminders(db)
        logger.info(
            "Scheduled reminders processed: %d created (scanned %d interviews, %d applications)",
            result.reminders_created,
            result.scanned_interviews,
            result.scanned_applications,
        )
        return {
            "status": "success",
            "reminders_created": result.reminders_created,
            "scanned_interviews": result.scanned_interviews,
            "scanned_applications": result.scanned_applications,
        }
    except Exception as exc:
        logger.error("Error processing scheduled reminders: %s", exc, exc_info=True)
        # Celery retry with exponential backoff; idempotency prevents duplicate notifications
        raise self.retry(exc=exc) from exc
    finally:
        db.close()
