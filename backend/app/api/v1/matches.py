import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.job import (
    JobFreshnessType,
    JobVerificationStatusType,
    WorkArrangementType,
)
from app.schemas.match import (
    JobMatchListResponse,
    JobMatchResponse,
    JobMatchRunRequest,
    JobMatchRunResult,
    JobMatchStateUpdate,
    UserMatchingPreferenceResponse,
    UserMatchingPreferenceUpdate,
)
from app.services.matching_service import MatchingService

matches_router = APIRouter(prefix="/matches", tags=["matches"])


@matches_router.get(
    "/preferences",
    response_model=UserMatchingPreferenceResponse,
    summary="Get user job matching preferences",
)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserMatchingPreferenceResponse:
    """Retrieve candidate career criteria and matching filters."""
    return MatchingService.get_user_preferences(db=db, user=current_user)


@matches_router.put(
    "/preferences",
    response_model=UserMatchingPreferenceResponse,
    summary="Update user job matching preferences",
)
def update_preferences(
    data: UserMatchingPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserMatchingPreferenceResponse:
    """Update target roles, location, arrangement, and salary preferences."""
    return MatchingService.update_user_preferences(db=db, user=current_user, data=data)


@matches_router.post(
    "/run",
    response_model=JobMatchRunResult,
    status_code=status.HTTP_200_OK,
    summary="Run deterministic matching on active jobs",
)
def run_matching(
    request: Optional[JobMatchRunRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobMatchRunResult:
    """Execute matching for the user's analyzed resume against open opportunities."""
    req = request or JobMatchRunRequest()
    return MatchingService.run_matching(db=db, user=current_user, request=req)


@matches_router.post(
    "/recompute",
    response_model=JobMatchRunResult,
    summary="Recompute matches with updated preferences",
)
def recompute_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobMatchRunResult:
    """Recompute all match scores using updated candidate criteria."""
    return MatchingService.recompute_matches(db=db, user=current_user)


@matches_router.get(
    "",
    response_model=JobMatchListResponse,
    summary="List ranked job matches",
)
def list_matches(
    role_family: Optional[str] = Query(None, description="Filter by role family"),
    location: Optional[str] = Query(None, description="Filter by location or city"),
    work_arrangement: Optional[WorkArrangementType] = Query(
        None, description="Filter by work arrangement"
    ),
    freshness: Optional[JobFreshnessType] = Query(
        None, description="Filter by freshness tier (recent, due_for_review, stale, unknown)"
    ),
    verification_status: Optional[JobVerificationStatusType] = Query(
        None, description="Filter by verification state"
    ),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum match score"),
    is_saved: Optional[bool] = Query(None, description="Filter by saved/bookmarked matches"),
    include_dismissed: bool = Query(
        False, description="Include dismissed opportunities in listings"
    ),
    sort_by: str = Query("score", description="'score' or 'date'"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobMatchListResponse:
    """Retrieve paginated and ranked matches with transparent evidence breakdown."""
    return MatchingService.list_matches(
        db=db,
        user=current_user,
        role_family=role_family,
        location=location,
        work_arrangement=work_arrangement,
        freshness=freshness,
        verification_status=verification_status,
        min_score=min_score,
        is_saved=is_saved,
        include_dismissed=include_dismissed,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )


@matches_router.get(
    "/{match_id}",
    response_model=JobMatchResponse,
    summary="Get match details and grounded evidence",
)
def get_match_detail(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobMatchResponse:
    """Retrieve score breakdown and resume citations for a specific match."""
    return MatchingService.get_match_detail(db=db, user=current_user, match_id=match_id)


@matches_router.patch(
    "/{match_id}",
    response_model=JobMatchResponse,
    summary="Save or dismiss a job match",
)
def update_match_state(
    match_id: uuid.UUID,
    data: JobMatchStateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobMatchResponse:
    """Bookmark or dismiss an opportunity."""
    return MatchingService.update_match_state(
        db=db, user=current_user, match_id=match_id, data=data
    )
