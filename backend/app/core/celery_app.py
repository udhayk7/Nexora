from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings

celery = Celery(
    "nexora_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    imports=["app.tasks.reminder_tasks", "app.tasks.discovery_tasks"],
    beat_schedule={
        "process-scheduled-reminders-every-15-mins": {
            "task": "process_scheduled_reminders_task",
            "schedule": 900.0,  # every 15 minutes
        },
        "scan-due-discovery-sources-hourly": {
            "task": "scan_all_due_sources_task",
            "schedule": 3600.0,  # every 1 hour
        },
    },
)
