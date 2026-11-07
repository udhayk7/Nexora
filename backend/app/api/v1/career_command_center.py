from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.career_command_center import (
    CareerFunnelResponse,
    CareerGoalsResponse,
    CareerGoalsUpdate,
    CareerOverviewKPIs,
    CareerReadinessResponse,
    PerformanceAnalyticsResponse,
    RecommendationsResponse,
)
from app.services.career_command_center_service import CareerCommandCenterService

router = APIRouter()


@router.get(
    "/overview",
    response_model=CareerOverviewKPIs,
    summary="Get Consolidated Career KPIs",
    description="Retrieve high-level job discovery, match, application, and preparation KPIs.",
)
def get_career_overview(
    date_range: Literal["30d", "90d", "all"] = Query(
        default="all", description="Date filter for activity metrics ('30d', '90d', 'all')"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerOverviewKPIs:
    return CareerCommandCenterService.get_overview(db=db, user=current_user, date_range=date_range)


@router.get(
    "/funnel",
    response_model=CareerFunnelResponse,
    summary="Get Visual Application Funnel",
    description="Retrieve 7-stage conversion funnel and outcomes based on application history.",
)
def get_career_funnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerFunnelResponse:
    return CareerCommandCenterService.get_funnel(db=db, user=current_user)


@router.get(
    "/readiness",
    response_model=CareerReadinessResponse,
    summary="Get Personalized Career Readiness",
    description="Retrieve demonstrated skills, market demand, and deterministic readiness score.",
)
def get_career_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerReadinessResponse:
    return CareerCommandCenterService.get_readiness(db=db, user=current_user)
    return CareerCommandCenterService.get_readiness(db=db, user=current_user)


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Get Recommended Next Actions",
    description="Retrieve prioritized, actionable next steps for the active job search.",
)
def get_recommended_next_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationsResponse:
    return CareerCommandCenterService.get_recommendations(db=db, user=current_user)


@router.get(
    "/analytics",
    response_model=PerformanceAnalyticsResponse,
    summary="Get Job Search Performance Analytics",
    description="Retrieve time-series activity, conversion rates, and role/company breakdowns.",
)
def get_performance_analytics(
    date_range: Literal["30d", "90d", "all"] = Query(
        default="all", description="Date filter for analytics ('30d', '90d', 'all')"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PerformanceAnalyticsResponse:
    return CareerCommandCenterService.get_analytics(db=db, user=current_user, date_range=date_range)


@router.get(
    "/goals",
    response_model=CareerGoalsResponse,
    summary="Get Career Goals & Preferences",
    description="Retrieve target roles, locations, minimum salary, and weekly application targets.",
)
def get_career_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerGoalsResponse:
    return CareerCommandCenterService.get_goals(db=db, user=current_user)


@router.put(
    "/goals",
    response_model=CareerGoalsResponse,
    summary="Update Career Goals & Preferences",
    description="Update target roles, salary, and application targets for matching engine.",
)
def update_career_goals(
    data: CareerGoalsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CareerGoalsResponse:
    return CareerCommandCenterService.update_goals(db=db, user=current_user, data=data)
