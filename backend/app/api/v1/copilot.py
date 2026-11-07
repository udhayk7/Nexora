import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.orchestration import (
    AgentExecutionRecordResponse,
    ApprovalActionRequest,
    ApprovalActionResponse,
    CopilotMessageCreateRequest,
    CopilotMessageResponse,
    CopilotSessionCreateRequest,
    CopilotSessionDetailResponse,
    CopilotSessionResponse,
    QuickActionRequest,
)
from app.services.orchestration.candidate_context import SharedCandidateContext
from app.services.orchestration.orchestrator import AIOrchestrator

logger = logging.getLogger("nexora.api.copilot")

router = APIRouter(prefix="/copilot", tags=["AI Career Copilot & Orchestration"])


@router.get(
    "/sessions",
    response_model=list[CopilotSessionResponse],
    summary="List candidate Copilot sessions",
    description="Returns active conversational intelligence sessions ordered by recency.",
)
def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CopilotSessionResponse]:
    return AIOrchestrator.list_user_sessions(db=db, user=current_user, limit=limit)


@router.post(
    "/sessions",
    response_model=CopilotSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new Copilot session",
    description="Initializes a new conversational session with candidate context snapshot.",
)
def create_session(
    payload: CopilotSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotSessionResponse:
    sess = AIOrchestrator.get_or_create_session(
        db=db,
        user=current_user,
        title=payload.title,
        session_type=payload.session_type,
    )
    return CopilotSessionResponse(
        id=sess.id,
        user_id=sess.user_id,
        title=sess.title,
        session_type=sess.session_type,
        is_active=sess.is_active,
        context_summary=sess.context_summary or {},
        message_count=0,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=CopilotSessionDetailResponse,
    summary="Get session details and message history",
    description="Retrieves conversational history, agent traces, and context snapshot.",
)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotSessionDetailResponse:
    return AIOrchestrator.get_session_detail(db=db, user=current_user, session_id=session_id)


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a Copilot session",
)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return AIOrchestrator.delete_session(db=db, user=current_user, session_id=session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=CopilotMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Post message to AI Career Copilot",
    description="Coordinates multi-agent pipeline, executes intent, and returns structured result.",
)
def post_message(
    session_id: uuid.UUID,
    payload: CopilotMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotMessageResponse:
    return AIOrchestrator.process_message(
        db=db,
        user=current_user,
        session_id=session_id,
        prompt=payload.content,
        target_job_id=payload.target_job_id,
        target_company_id=payload.target_company_id,
    )


@router.post(
    "/quick-action",
    response_model=CopilotMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger pre-configured multi-agent quick action",
    description=(
        "Executes curated workflows: career diagnosis, job discovery, application prep, etc."
    ),
)
def execute_quick_action(
    payload: QuickActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CopilotMessageResponse:
    return AIOrchestrator.execute_quick_action(
        db=db,
        user=current_user,
        action=payload.action,
        target_id=payload.target_id,
        parameters=payload.parameters,
    )


@router.get(
    "/executions/{workflow_id}",
    response_model=list[AgentExecutionRecordResponse],
    summary="Get multi-agent workflow execution audit records",
    description=(
        "Audit transparency endpoint tracking individual agent steps, latencies, and tokens."
    ),
)
def get_workflow_executions(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentExecutionRecordResponse]:
    return AIOrchestrator.get_workflow_executions(db=db, user=current_user, workflow_id=workflow_id)


@router.post(
    "/approvals/{record_id}",
    response_model=ApprovalActionResponse,
    summary="Approve or reject a consequential action proposal",
    description="Explicit candidate gate for actions requiring sign-off.",
)
def handle_approval(
    record_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalActionResponse:
    return AIOrchestrator.handle_action_approval(
        db=db,
        user=current_user,
        record_id=record_id,
        action=payload.action,
        notes=payload.notes,
    )


@router.get(
    "/context-preview",
    summary="Preview shared candidate context projection",
    description=(
        "Inspect lean facts, verified skills, and metrics accessible to specialized agents."
    ),
)
def get_context_preview(
    target_job_id: Optional[uuid.UUID] = None,
    target_company_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    ctx = SharedCandidateContext.build(
        db=db,
        user=current_user,
        target_job_id=target_job_id,
        target_company_id=target_company_id,
    )
    return {
        "candidate": ctx.to_lean_summary(),
        "verified_skills": ctx.verified_skills,
        "verified_projects": ctx.verified_projects,
        "verified_education": ctx.verified_education,
        "target_roles": ctx.target_roles,
        "preferred_locations": ctx.preferred_locations,
        "preferred_arrangements": ctx.preferred_arrangements,
        "active_applications_count": ctx.active_applications_count,
        "interviews_scheduled_count": ctx.interviews_scheduled_count,
        "career_readiness_score": ctx.career_readiness_score,
        "portfolio_slug": ctx.portfolio_slug,
        "target_job_title": ctx.target_job_title,
        "target_company_name": ctx.target_company_name,
    }
