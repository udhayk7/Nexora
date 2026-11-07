"""
Learning Roadmaps & Skill Development API endpoints.
Provides skill gap analysis, personalized roadmap lifecycle, curated educational resources,
milestone progress, practical project tracking, and learning analytics.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.learning_roadmap import (
    LearningActivityCreate,
    LearningActivityResponse,
    LearningAnalyticsResponse,
    LearningMilestoneResponse,
    LearningMilestoneUpdate,
    LearningProjectCreate,
    LearningProjectResponse,
    LearningProjectUpdate,
    LearningResourceCreate,
    LearningResourceResponse,
    LearningRoadmapResponse,
    LearningRoadmapStatusUpdate,
    LearningRoadmapSummary,
    ProjectRecommendationResponse,
    RoadmapGenerateRequest,
    SkillGapAnalysisResponse,
)
from app.services.learning_roadmap_service import LearningRoadmapService

router = APIRouter(prefix="/learning-roadmaps", tags=["Learning Roadmaps"])


# ---------------------------------------------------------------------------
# 1. Skill Gap Analysis
# ---------------------------------------------------------------------------


@router.get(
    "/skill-gaps",
    response_model=SkillGapAnalysisResponse,
    summary="Get personalized skill gap analysis",
    description=(
        "Synthesize demonstrated resume skills, job market demand, "
        "interview weaknesses, and career goals into prioritized skill gaps."
    ),
)
def get_skill_gaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SkillGapAnalysisResponse:
    return LearningRoadmapService.get_skill_gaps(db=db, user=current_user)


# ---------------------------------------------------------------------------
# 2. Learning Analytics
# ---------------------------------------------------------------------------


@router.get(
    "/analytics",
    response_model=LearningAnalyticsResponse,
    summary="Get learning progress analytics",
    description=(
        "Synthesize total hours learned, weekly study velocity, "
        "completed milestones, and skills in progress."
    ),
)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningAnalyticsResponse:
    return LearningRoadmapService.get_analytics(db=db, user=current_user)


# ---------------------------------------------------------------------------
# 3. Learning Resources
# ---------------------------------------------------------------------------


@router.get(
    "/resources/catalog",
    response_model=list[LearningResourceResponse],
    summary="Browse educational resources",
    description=(
        "Explore curated educational resources from official documentation, "
        "FreeCodeCamp, MDN, Microsoft Learn, AWS, etc., plus user custom resources."
    ),
)
def list_resources(
    skill: Optional[str] = Query(None, description="Filter by skill (e.g. Python, FastAPI, React)"),
    difficulty: Optional[str] = Query(
        None, description="Filter by difficulty (beginner, intermediate, advanced)"
    ),
    cost_tier: Optional[str] = Query(None, description="Filter by cost (free, paid, freemium)"),
    search: Optional[str] = Query(None, description="Search keyword across title and provider"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LearningResourceResponse]:
    resources = LearningRoadmapService.list_resources(
        db=db,
        user=current_user,
        skill=skill,
        difficulty=difficulty,
        cost_tier=cost_tier,
        search=search,
        limit=limit,
    )
    return [LearningResourceResponse.model_validate(r) for r in resources]


@router.post(
    "/resources/custom",
    response_model=LearningResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add custom learning resource bookmark",
    description="Add a personal learning resource bookmark for skill practice.",
)
def create_custom_resource(
    payload: LearningResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningResourceResponse:
    resource = LearningRoadmapService.create_custom_resource(
        db=db,
        user=current_user,
        data=payload,
    )
    return LearningResourceResponse.model_validate(resource)


@router.delete(
    "/resources/custom/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete custom learning resource",
    description="Delete a candidate-created custom bookmark.",
)
def delete_custom_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    LearningRoadmapService.delete_custom_resource(
        db=db,
        user=current_user,
        resource_id=resource_id,
    )


# ---------------------------------------------------------------------------
# 4. Learning Activities
# ---------------------------------------------------------------------------


@router.post(
    "/activities",
    response_model=LearningActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log learning activity",
    description="Record study, coding, or reading hours and progress notes.",
)
def log_activity(
    payload: LearningActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningActivityResponse:
    activity = LearningRoadmapService.log_activity(
        db=db,
        user=current_user,
        data=payload,
    )
    return LearningActivityResponse.model_validate(activity)


@router.get(
    "/activities",
    response_model=list[LearningActivityResponse],
    summary="List learning activity history",
    description="Retrieve chronological log of study and practice sessions.",
)
def list_activities(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LearningActivityResponse]:
    activities = LearningRoadmapService.get_activities(
        db=db,
        user=current_user,
        limit=limit,
    )
    return [LearningActivityResponse.model_validate(a) for a in activities]


# ---------------------------------------------------------------------------
# 5. Practical Projects
# ---------------------------------------------------------------------------


@router.get(
    "/projects/recommendations",
    response_model=list[ProjectRecommendationResponse],
    summary="Get recommended portfolio projects",
    description="Recommend practical portfolio projects addressing missing technical skills.",
)
def get_project_recommendations(
    target_role: Optional[str] = Query(None, description="Target career track"),
    limit: int = Query(4, ge=1, le=8),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectRecommendationResponse]:
    return LearningRoadmapService.get_project_recommendations(
        db=db,
        user=current_user,
        target_role=target_role,
        limit=limit,
    )


@router.get(
    "/projects",
    response_model=list[LearningProjectResponse],
    summary="List candidate tracked projects",
    description="List practical projects created and tracked by candidate.",
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LearningProjectResponse]:
    projects = LearningRoadmapService.list_projects(db=db, user=current_user)
    return [LearningProjectResponse.model_validate(p) for p in projects]


@router.post(
    "/projects",
    response_model=LearningProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or track a practical project",
    description="Create a project to demonstrate practical competency with functional specs.",
)
def create_project(
    payload: LearningProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningProjectResponse:
    project = LearningRoadmapService.create_project(
        db=db,
        user=current_user,
        data=payload,
    )
    return LearningProjectResponse.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=LearningProjectResponse,
    summary="Update project progress and portfolio readiness",
    description=(
        "Update project status, repository URL, live demo URL, and architecture evidence notes."
    ),
)
def update_project(
    project_id: uuid.UUID,
    payload: LearningProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningProjectResponse:
    project = LearningRoadmapService.update_project(
        db=db,
        user=current_user,
        project_id=project_id,
        update=payload,
    )
    return LearningProjectResponse.model_validate(project)


# ---------------------------------------------------------------------------
# 6. Milestones
# ---------------------------------------------------------------------------


@router.patch(
    "/milestones/{milestone_id}",
    response_model=LearningMilestoneResponse,
    summary="Update milestone progress",
    description=(
        "Update milestone status (not_started, in_progress, completed), hours spent, and exercises."
    ),
)
def update_milestone(
    milestone_id: uuid.UUID,
    payload: LearningMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningMilestoneResponse:
    milestone = LearningRoadmapService.update_milestone(
        db=db,
        user=current_user,
        milestone_id=milestone_id,
        update=payload,
    )
    return LearningMilestoneResponse.model_validate(milestone)


# ---------------------------------------------------------------------------
# 7. Roadmaps Root & Dynamic Paths
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[LearningRoadmapSummary],
    summary="List learning roadmaps",
    description="List learning roadmaps belonging to the authenticated candidate.",
)
def list_roadmaps(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status (active, paused, completed, archived)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LearningRoadmapSummary]:
    roadmaps = LearningRoadmapService.get_user_roadmaps(
        db=db, user=current_user, status=status_filter
    )
    summaries: list[LearningRoadmapSummary] = []
    for rm in roadmaps:
        all_m = rm.milestones
        done_m = sum(1 for m in all_m if m.status in ("completed", "skipped"))
        summaries.append(
            LearningRoadmapSummary(
                id=rm.id,
                title=rm.title,
                target_role=rm.target_role,
                target_skills=rm.target_skills,
                status=rm.status,
                difficulty_level=rm.difficulty_level,
                total_estimated_hours=rm.total_estimated_hours,
                completed_hours=rm.completed_hours,
                completion_percentage=rm.completion_percentage,
                milestones_count=len(all_m),
                completed_milestones_count=done_m,
                created_at=rm.created_at,
            )
        )
    return summaries


@router.post(
    "",
    response_model=LearningRoadmapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized learning roadmap",
    description="Generate a 4-stage learning roadmap adapted to candidate's demonstrated skills.",
)
def create_roadmap(
    payload: RoadmapGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningRoadmapResponse:
    roadmap = LearningRoadmapService.generate_and_save_roadmap(
        db=db,
        user=current_user,
        request=payload,
    )
    return LearningRoadmapResponse.model_validate(roadmap)


@router.get(
    "/{roadmap_id}",
    response_model=LearningRoadmapResponse,
    summary="Get learning roadmap detail",
    description="Retrieve a complete roadmap including stages, exercises, and completion progress.",
)
def get_roadmap(
    roadmap_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningRoadmapResponse:
    roadmap = LearningRoadmapService.get_roadmap_detail(
        db=db,
        user=current_user,
        roadmap_id=roadmap_id,
    )
    return LearningRoadmapResponse.model_validate(roadmap)


@router.patch(
    "/{roadmap_id}/status",
    response_model=LearningRoadmapResponse,
    summary="Update roadmap status",
    description="Update roadmap status (active, paused, completed, archived).",
)
def update_roadmap_status(
    roadmap_id: uuid.UUID,
    payload: LearningRoadmapStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LearningRoadmapResponse:
    roadmap = LearningRoadmapService.update_roadmap_status(
        db=db,
        user=current_user,
        roadmap_id=roadmap_id,
        status=payload.status,
    )
    return LearningRoadmapResponse.model_validate(roadmap)


@router.delete(
    "/{roadmap_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a learning roadmap",
    description="Delete a learning roadmap and its milestones permanently.",
)
def delete_roadmap(
    roadmap_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    LearningRoadmapService.delete_roadmap(
        db=db,
        user=current_user,
        roadmap_id=roadmap_id,
    )
