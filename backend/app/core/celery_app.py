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
    imports=[
        "app.tasks.reminder_tasks",
        "app.tasks.discovery_tasks",
        "app.tasks.workflow_tasks",
        "app.tasks.networking_tasks",
        "app.tasks.orchestration_tasks",
    ],
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

# Apply optional Redis production security configuration
if settings.REDIS_PASSWORD:
    celery.conf.update(
        broker_transport_options={"password": settings.REDIS_PASSWORD},
        result_backend_transport_options={"password": settings.REDIS_PASSWORD},
    )
if settings.REDIS_SSL:
    celery.conf.update(
        broker_use_ssl={"ssl_cert_reqs": None},
        redis_backend_use_ssl={"ssl_cert_reqs": None},
    )
