import logging
import uuid
from typing import Any, Optional

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.models.user import User
from app.services.orchestration.orchestrator import AIOrchestrator

logger = logging.getLogger("nexora.tasks.orchestration")


@celery.task(name="run_orchestration_workflow_task", bind=True)
def run_orchestration_workflow_task(
    self: Any,
    session_id_str: str,
    user_id_str: str,
    prompt: str,
    target_job_id_str: Optional[str] = None,
    target_company_id_str: Optional[str] = None,
) -> dict[str, Any]:
    """Celery background task for decoupled execution of complex multi-agent workflows."""
    db = SessionLocal()
    try:
        user_id = uuid.UUID(user_id_str)
        session_id = uuid.UUID(session_id_str)
        target_job_id = uuid.UUID(target_job_id_str) if target_job_id_str else None
        target_company_id = uuid.UUID(target_company_id_str) if target_company_id_str else None

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error("User %s not found for orchestration task", user_id_str)
            return {"status": "failed", "error": "User not found"}

        res = AIOrchestrator.process_message(
            db=db,
            user=user,
            session_id=session_id,
            prompt=prompt,
            target_job_id=target_job_id,
            target_company_id=target_company_id,
        )
        return {
            "status": "completed",
            "message_id": str(res.id),
            "intent": res.intent,
            "agent_steps": len(res.agent_trace),
        }
    except Exception as exc:
        logger.error("Error running orchestration workflow task: %s", exc, exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
