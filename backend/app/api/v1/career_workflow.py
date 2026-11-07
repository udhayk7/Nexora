import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.workflow import CareerWorkflowRun
from app.schemas.workflow import (
    ApprovePreparationRequest,
    CareerWorkflowRunResponse,
    GmailExecuteRequest,
    OnboardingConfirmRequest,
    OnboardingResultResponse,
    OnboardingStartRequest,
    PortalConfirmRequest,
    PortalOpenResponse,
    PreparationDetailResponse,
    PreparationStartRequest,
    UnifiedDiscoveryResponse,
    WorkflowDashboardResponse,
)
from app.services.career_workflow_service import CareerWorkflowService

logger = logging.getLogger("nexora.api.career_workflow")

router = APIRouter(prefix="/career-workflow", tags=["Career Workflow & Automation"])


# ---------------------------------------------------------------------------
# 1. Central Career Workflow Dashboard
# ---------------------------------------------------------------------------


@router.get(
    "/dashboard",
    response_model=WorkflowDashboardResponse,
    summary="Get unified career workflow dashboard",
    description=(
        "Aggregated pipeline metrics, candidate onboarding status, "
        "action items, and recent workflow runs."
    ),
)
def get_workflow_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowDashboardResponse:
    return CareerWorkflowService.get_workflow_dashboard(db=db, user=current_user)


# ---------------------------------------------------------------------------
# 2. Unified Candidate Onboarding
# ---------------------------------------------------------------------------


@router.post(
    "/onboarding/start",
    response_model=OnboardingResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Start connected candidate onboarding",
    description=(
        "Extracts candidate profile from resume, infers target roles and preferences, "
        "and initializes job matching."
    ),
)
def start_onboarding(
    payload: OnboardingStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingResultResponse:
    return CareerWorkflowService.start_onboarding_workflow(
        db=db,
        user=current_user,
        resume_id=payload.resume_id,
        preferences_override=payload.preferences_override,
    )


@router.post(
    "/onboarding/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm candidate onboarding preferences",
    description=(
        "Allows candidate to review, correct, and approve extracted and inferred "
        "career preferences."
    ),
)
def confirm_onboarding(
    payload: OnboardingConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return CareerWorkflowService.confirm_onboarding_review(
        db=db,
        user=current_user,
        data=payload,
    )


# ---------------------------------------------------------------------------
# 3. Unified Job Discovery & Prioritization
# ---------------------------------------------------------------------------


@router.get(
    "/discovery",
    response_model=UnifiedDiscoveryResponse,
    summary="Unified job discovery and opportunity ranking",
    description=(
        "Discovers active jobs with entry-level detection, premier employer tier "
        "prioritization, and verification provenance."
    ),
)
def get_unified_discovery(
    filter_entry_level: bool = Query(
        True, description="Filter specifically for entry-level and fresher opportunities"
    ),
    prioritize_tiers: bool = Query(
        True, description="Prioritize Product companies, MNCs, GCCs, and top tech employers"
    ),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnifiedDiscoveryResponse:
    return CareerWorkflowService.get_unified_discovery(
        db=db,
        user=current_user,
        filter_entry_level=filter_entry_level,
        prioritize_tiers=prioritize_tiers,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# 4. Intelligent Application Preparation Workspace
# ---------------------------------------------------------------------------


@router.post(
    "/preparation/start",
    response_model=PreparationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize application preparation workspace",
    description=(
        "Connects job intelligence, resume tailoring, cover letter, email, "
        "screening Q&A, and company research."
    ),
)
def start_preparation(
    payload: PreparationStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationDetailResponse:
    return CareerWorkflowService.get_or_create_preparation_workspace(
        db=db,
        user=current_user,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
    )


@router.get(
    "/preparation/{job_id}",
    response_model=PreparationDetailResponse,
    summary="Get job preparation materials",
    description="Returns all 8 unified application preparation assets for a specific job.",
)
def get_preparation(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationDetailResponse:
    return CareerWorkflowService.get_or_create_preparation_workspace(
        db=db,
        user=current_user,
        job_id=job_id,
    )


@router.post(
    "/preparation/{job_id}/approve",
    response_model=PreparationDetailResponse,
    summary="Approve application preparation",
    description=(
        "Candidate explicit approval gate: validates materials and sets state to 'ready_to_apply'."
    ),
)
def approve_preparation(
    job_id: uuid.UUID,
    payload: ApprovePreparationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreparationDetailResponse:
    return CareerWorkflowService.approve_preparation(
        db=db,
        user=current_user,
        job_id=job_id,
        channel=payload.channel,
        notes=payload.notes,
    )


# ---------------------------------------------------------------------------
# 5. Application Execution Workflow
# ---------------------------------------------------------------------------


@router.post(
    "/execution/portal-open/{job_id}",
    response_model=PortalOpenResponse,
    summary="Open official application portal",
    description=(
        "Provides verified portal URL and assisted form auto-fill guidance. "
        "Strictly does not claim submission."
    ),
)
def open_portal(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortalOpenResponse:
    data = CareerWorkflowService.open_application_portal(
        db=db,
        user=current_user,
        job_id=job_id,
    )
    return PortalOpenResponse(
        portal_url=data["portal_url"],
        assisted_form_data=data["assisted_form_data"],
        execution_status=data["execution_status"],
        opened_at=data["opened_at"],
    )


@router.post(
    "/execution/portal-confirm/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Confirm completed portal submission",
    description=(
        "Candidate explicitly confirms portal form submission, "
        "moving state to 'submitted_and_confirmed'."
    ),
)
def confirm_portal_submission(
    job_id: uuid.UUID,
    payload: PortalConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return CareerWorkflowService.confirm_portal_submission(
        db=db,
        user=current_user,
        job_id=job_id,
        confirmation_notes=payload.confirmation_notes,
    )


@router.post(
    "/execution/gmail-send/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Execute Gmail application dispatch",
    description=(
        "Sends approved recruiter email via Gmail with attachments. Explicit confirmation required."
    ),
)
def execute_gmail_send(
    job_id: uuid.UUID,
    payload: GmailExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return CareerWorkflowService.execute_gmail_application(
        db=db,
        user=current_user,
        job_id=job_id,
        email_id=payload.email_id,
        confirm_send=payload.confirm_send,
    )


@router.post(
    "/execution/withdraw/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Withdraw application",
    description="Withdraws candidate application from active consideration.",
)
def withdraw_application(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return CareerWorkflowService.withdraw_application(
        db=db,
        user=current_user,
        job_id=job_id,
    )


# ---------------------------------------------------------------------------
# 6. Workflow Orchestration & Run Management
# ---------------------------------------------------------------------------


@router.get(
    "/runs",
    response_model=list[CareerWorkflowRunResponse],
    summary="List career workflow runs",
    description="Lists past and active workflow orchestration runs for authenticated candidate.",
)
def list_workflow_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CareerWorkflowRunResponse]:
    runs = (
        db.query(CareerWorkflowRun)
        .filter(CareerWorkflowRun.user_id == current_user.id)
        .order_by(CareerWorkflowRun.created_at.desc())
        .limit(20)
        .all()
    )
    return [CareerWorkflowRunResponse.model_validate(r) for r in runs]


@router.post(
    "/runs/{run_id}/cancel",
    response_model=CareerWorkflowRunResponse,
    summary="Cancel workflow run",
    description="Cancels an eligible pending or running workflow run.",
)
def cancel_workflow_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerWorkflowRunResponse:
    run = CareerWorkflowService.cancel_workflow_run(
        db=db,
        user=current_user,
        run_id=run_id,
    )
    return CareerWorkflowRunResponse.model_validate(run)
