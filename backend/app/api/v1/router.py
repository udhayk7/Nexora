from fastapi import APIRouter

from app.api.v1.applications import applications_router
from app.api.v1.auth import auth_router
from app.api.v1.companies import companies_router
from app.api.v1.jobs import jobs_router
from app.api.v1.matches import matches_router
from app.api.v1.resumes import resumes_router
from app.api.v1.tailoring import tailoring_router
from app.api.v1.users import users_router
from app.core.config import settings
from app.schemas.health import HealthResponse

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Return health status of the API."""
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )


# Mount feature routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(resumes_router)
api_router.include_router(companies_router)
api_router.include_router(jobs_router)
api_router.include_router(matches_router)
api_router.include_router(tailoring_router)
api_router.include_router(applications_router)
