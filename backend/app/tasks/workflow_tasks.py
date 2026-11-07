"""Celery background tasks for unified career workflow orchestration."""

import logging
import uuid
from typing import Any

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.models.workflow import CareerWorkflowRun
from app.services.career_workflow_service import CareerWorkflowService

logger = logging.getLogger("nexora.tasks.workflow")


@celery.task(
    name="run_career_workflow_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_career_workflow_task(self: Any, workflow_run_id_str: str) -> dict[str, Any]:
    """Execute career workflow asynchronously with bounded retries and status logging."""
    logger.info("Executing run_career_workflow_task for run: %s", workflow_run_id_str)
    db = SessionLocal()
    try:
        run_id = uuid.UUID(workflow_run_id_str)
        run = db.query(CareerWorkflowRun).filter(CareerWorkflowRun.id == run_id).first()
        if not run:
            logger.warning("Workflow run %s not found", workflow_run_id_str)
            return {"status": "not_found", "run_id": workflow_run_id_str}

        if run.status == "cancelled":
            logger.info("Workflow run %s was cancelled before execution", workflow_run_id_str)
            return {"status": "cancelled", "run_id": workflow_run_id_str}

        # Update running status
        run.status = "running"
        run.celery_task_id = self.request.id
        db.commit()

        # Handle workflow type
        if run.workflow_type == "onboarding":
            resume_id = (
                uuid.UUID(run.step_data.get("resume_id"))
                if run.step_data.get("resume_id")
                else None
            )
            CareerWorkflowService.start_onboarding_workflow(
                db=db,
                user=run.user,
                resume_id=resume_id,
            )
        elif run.workflow_type == "application_preparation":
            if run.target_job_id:
                CareerWorkflowService.get_or_create_preparation_workspace(
                    db=db,
                    user=run.user,
                    job_id=run.target_job_id,
                )

        logger.info("Async workflow run %s completed successfully", workflow_run_id_str)
        return {"status": "success", "run_id": workflow_run_id_str}

    except Exception as exc:
        logger.error("Error running workflow task %s: %s", workflow_run_id_str, exc, exc_info=True)
        db.rollback()
        # Update run error message
        try:
            r = (
                db.query(CareerWorkflowRun)
                .filter(CareerWorkflowRun.id == uuid.UUID(workflow_run_id_str))
                .first()
            )
            if r:
                r.retry_count += 1
                r.error_message = str(exc)
                if r.retry_count >= r.max_retries:
                    r.status = "failed"
                db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc) from exc
    finally:
        db.close()
