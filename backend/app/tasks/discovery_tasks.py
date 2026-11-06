"""Celery background tasks for automated job discovery and feed ingestion."""

import logging
import uuid
from typing import Any

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.services.discovery.discovery_service import JobDiscoveryService

logger = logging.getLogger("nexora.tasks.discovery")


@celery.task(
    name="scan_all_due_sources_task",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def scan_all_due_sources_task(self: Any) -> dict[str, Any]:
    """Periodic task scanning all enabled discovery sources that are due based on scan_frequency."""
    logger.info("Executing scan_all_due_sources_task")
    db = SessionLocal()
    try:
        result = JobDiscoveryService.scan_all_sources(db, only_due=True)
        logger.info(
            "Batch discovery scan completed: %d scanned, %d new, %d updated, %d failed",
            result.sources_scanned,
            result.total_jobs_imported,
            result.total_jobs_updated,
            result.failed_sources,
        )
        return {
            "status": "success",
            "sources_scanned": result.sources_scanned,
            "total_jobs_imported": result.total_jobs_imported,
            "total_jobs_updated": result.total_jobs_updated,
            "failed_sources": result.failed_sources,
        }
    except Exception as exc:
        logger.error("Error running batch discovery scan: %s", exc, exc_info=True)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery.task(
    name="scan_single_company_source_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def scan_single_company_source_task(self: Any, source_id_str: str) -> dict[str, Any]:
    """Background task to scan a single company source asynchronously."""
    logger.info("Executing scan_single_company_source_task for source: %s", source_id_str)
    db = SessionLocal()
    try:
        source_id = uuid.UUID(source_id_str)
        result = JobDiscoveryService.scan_source(db, source_id, scan_type="scheduled")
        return {
            "status": result.status,
            "source_id": str(result.source_id),
            "jobs_found": result.jobs_found,
            "jobs_imported": result.jobs_imported,
            "jobs_updated": result.jobs_updated,
            "message": result.message,
        }
    except Exception as exc:
        logger.error("Error scanning single source %s: %s", source_id_str, exc, exc_info=True)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()
