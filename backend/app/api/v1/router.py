from fastapi import APIRouter

from app.api.v1.applications import applications_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.auth import auth_router
from app.api.v1.companies import companies_router
from app.api.v1.company_intelligence import router as company_intelligence_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.interview_prep import router as interview_prep_router
from app.api.v1.jobs import jobs_router
from app.api.v1.matches import matches_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.recommendations import router as recommendations_router
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
api_router.include_router(notifications_router)
api_router.include_router(discovery_router, prefix="/discovery", tags=["Job Discovery"])
api_router.include_router(recommendations_router)
api_router.include_router(assistant_router)
api_router.include_router(integrations_router)
api_router.include_router(interview_prep_router)
api_router.include_router(company_intelligence_router)
