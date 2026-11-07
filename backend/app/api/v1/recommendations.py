import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.recommendation import (
    AIJobMatchResponse,
    JobIntelligenceResponse,
    RecommendationListResponse,
    RecommendationRefreshRequest,
    RecommendationRefreshResponse,
    RecommendationStateResponse,
    RecommendationStateUpdateRequest,
)
from app.services.job_intelligence_service import JobIntelligenceService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations & AI Job Intelligence"])


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="Retrieve personalized job recommendations",
)
def get_recommendations(
    resume_version_id: Optional[uuid.UUID] = Query(None, description="Optional resume version ID"),
    role_family: Optional[str] = Query(None, description="Filter by role family"),
    location: Optional[str] = Query(None, description="Filter by location/city/country"),
    work_arrangement: Optional[str] = Query(
        None, description="Filter: remote, hybrid, on_site, or all"
    ),
    seniority: Optional[str] = Query(
        None, description="Filter: fresher, junior, mid, senior, or all"
    ),
    verification_status: Optional[str] = Query(
        None, description="Filter: verified, corroborated, or all"
    ),
    min_score: Optional[float] = Query(
        None, ge=0.0, le=100.0, description="Minimum recommendation score"
    ),
    salary_disclosed_only: bool = Query(
        False, description="Filter to jobs with disclosed salary only"
    ),
    include_applied: bool = Query(False, description="Include jobs already applied to"),
    search_query: Optional[str] = Query(
        None, description="Text search on title, location, role family"
    ),
    sort_by: str = Query(
        "recommendation_score",
        description="Sort: recommendation_score, deterministic_score, newest, salary",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationListResponse:
    """Retrieve personalized, ranked job recommendations using deterministic matching evidence,

    job intelligence, freshness, and AI compatibility assessments.
    """
    return RecommendationService.get_recommendations(
        db=db,
        user=current_user,
        resume_version_id=resume_version_id,
        role_family=role_family,
        location=location,
        work_arrangement=work_arrangement,
        seniority=seniority,
        verification_status=verification_status,
        min_score=min_score,
        salary_disclosed_only=salary_disclosed_only,
        include_applied=include_applied,
        search_query=search_query,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/refresh",
    response_model=RecommendationRefreshResponse,
    summary="Refresh personalized recommendations",
)
def refresh_recommendations(
    request: RecommendationRefreshRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationRefreshResponse:
    """Re-evaluate matches and refresh recommendations, with optional top-N AI evaluation."""
    return RecommendationService.refresh_recommendations(
        db=db,
        user=current_user,
        request=request,
    )


@router.post(
    "/jobs/{job_id}/ai-match",
    response_model=AIJobMatchResponse,
    summary="Run AI-assisted resume-to-job matching assessment",
)
def run_ai_match(
    job_id: uuid.UUID,
    resume_version_id: Optional[uuid.UUID] = Query(None, description="Optional resume version ID"),
    force_refresh: bool = Query(False, description="Force re-evaluation bypassing cache"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIJobMatchResponse:
    """Run an AI-assisted evaluation between the user's selected resume and target job."""
    return RecommendationService.evaluate_ai_match(
        db=db,
        user=current_user,
        job_id=job_id,
        resume_version_id=resume_version_id,
        force_refresh=force_refresh,
    )


@router.get(
    "/jobs/{job_id}/ai-match",
    response_model=AIJobMatchResponse,
    summary="Retrieve AI match assessment for a job",
)
def get_ai_match(
    job_id: uuid.UUID,
    resume_version_id: Optional[uuid.UUID] = Query(None, description="Optional resume version ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIJobMatchResponse:
    """Retrieve existing AI match assessment for a job, or 404 if not yet evaluated."""
    res = RecommendationService.get_ai_match_evaluation(
        db=db,
        user=current_user,
        job_id=job_id,
        resume_version_id=resume_version_id,
    )
    if not res:
        raise NotFoundError("AI match evaluation has not been run for this job yet")
    return res


@router.get(
    "/jobs/{job_id}/intelligence",
    response_model=JobIntelligenceResponse,
    summary="Retrieve structured job description intelligence",
)
def get_job_intelligence(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobIntelligenceResponse:
    """Retrieve structured requirements, skills, and evidence extracted from the job description."""
    return JobIntelligenceService.get_by_job_id(db=db, job_id=job_id)


@router.post(
    "/jobs/{job_id}/intelligence",
    response_model=JobIntelligenceResponse,
    summary="Analyze or refresh job description intelligence",
)
def analyze_job_intelligence(
    job_id: uuid.UUID,
    force_refresh: bool = Query(False, description="Force re-extraction bypassing cache"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobIntelligenceResponse:
    """Extract or re-extract structured requirements and evidence from job description."""
    from app.models.job import Job

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise NotFoundError("Job opportunity not found")

    intelligence = JobIntelligenceService.get_or_create(db=db, job=job, force_refresh=force_refresh)
    return JobIntelligenceResponse.model_validate(intelligence)


@router.patch(
    "/jobs/{job_id}/state",
    response_model=RecommendationStateResponse,
    summary="Update saved or dismissed state of a recommended job",
)
def update_job_recommendation_state(
    job_id: uuid.UUID,
    data: RecommendationStateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationStateResponse:
    """Save or dismiss a recommended job opportunity."""
    return RecommendationService.update_opportunity_state(
        db=db,
        user=current_user,
        job_id=job_id,
        is_saved=data.is_saved,
        is_dismissed=data.is_dismissed,
    )

