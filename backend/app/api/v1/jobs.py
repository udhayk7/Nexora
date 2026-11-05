import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.job import (
    FeedIngestRequest,
    FeedIngestResult,
    JobCreate,
    JobDetailResponse,
    JobDuplicateCheckResponse,
    JobFreshnessType,
    JobListResponse,
    JobRecheckRequest,
    JobRecheckResponse,
    JobSourceCreate,
    JobSourceResponse,
    JobStatusType,
    JobUpdate,
    JobVerificationCreate,
    JobVerificationResponse,
    JobVerificationStatusType,
    JobVerifyRequest,
    WorkArrangementType,
)
from app.services.job_service import JobService

jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])


@jobs_router.get(
    "",
    response_model=JobListResponse,
    summary="List and filter job opportunities",
)
def list_jobs(
    search: Optional[str] = Query(None, description="Search term across title, location, and desc"),
    company_id: Optional[uuid.UUID] = Query(None, description="Filter by company UUID"),
    role_family: Optional[str] = Query(None, description="Filter by role family"),
    skills: Optional[str] = Query(None, description="Filter by skill or technology tag"),
    seniority: Optional[str] = Query(None, description="Filter by seniority level"),
    location: Optional[str] = Query(None, description="Filter by location or city"),
    work_arrangement: Optional[WorkArrangementType] = Query(
        None, description="Filter by work arrangement"
    ),
    verification_status: Optional[JobVerificationStatusType] = Query(
        None, description="Filter by verification state"
    ),
    freshness: Optional[JobFreshnessType] = Query(
        None, description="Filter by freshness tier (recent, due_for_review, stale, unknown)"
    ),
    job_status: Optional[JobStatusType] = Query(
        "active", description="Filter by active/expired status"
    ),
    unassociated_only: bool = Query(
        False, description="Filter to jobs with no company association"
    ),
    user_only: bool = Query(False, description="Filter to jobs submitted by current user"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobListResponse:
    """Retrieve paginated and filtered job opportunities."""
    return JobService.list_jobs(
        db=db,
        search=search,
        company_id=company_id,
        role_family=role_family,
        skills=skills,
        seniority=seniority,
        location=location,
        work_arrangement=work_arrangement,
        verification_status=verification_status,
        freshness=freshness,
        job_status=job_status,
        unassociated_only=unassociated_only,
        user_only=user_only,
        current_user=current_user,
        page=page,
        per_page=per_page,
    )


@jobs_router.get(
    "/duplicates/check",
    response_model=JobDuplicateCheckResponse,
    summary="Check for potential duplicate job postings",
)
def check_duplicates(
    job_url: str = Query(..., min_length=1, description="Job URL to check canonical matching"),
    title: Optional[str] = Query(None, description="Job title to check"),
    company_id: Optional[uuid.UUID] = Query(None, description="Optional company UUID"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> JobDuplicateCheckResponse:
    """Check for duplicate job records by canonical URL or company/title clustering."""
    return JobService.check_duplicates(
        db=db, job_url=job_url, title=title, company_id=company_id
    )


@jobs_router.post(
    "",
    response_model=JobDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new job opportunity",
)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobDetailResponse:
    """Create a new job opportunity record with provenance citation."""
    return JobService.create_job(db=db, user=current_user, data=data)


@jobs_router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get detailed job listing and provenance",
)
def get_job_detail(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> JobDetailResponse:
    """Retrieve full job details, company profile, and discovery sources."""
    return JobService.get_job_detail(db=db, job_id=job_id)


@jobs_router.patch(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Update job listing details",
)
def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobDetailResponse:
    """Update job listing metadata with authorization checks."""
    return JobService.update_job(db=db, user=current_user, job_id=job_id, data=data)


@jobs_router.post(
    "/{job_id}/verify",
    response_model=JobDetailResponse,
    summary="Update verification or active state",
)
def verify_job(
    job_id: uuid.UUID,
    data: JobVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobDetailResponse:
    """Update verification status with mandatory evidence notes."""
    return JobService.verify_job(db=db, user=current_user, job_id=job_id, data=data)


@jobs_router.get(
    "/{job_id}/verifications",
    response_model=list[JobVerificationResponse],
    summary="Get verification and check history for a job",
)
def get_job_verifications(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> list[JobVerificationResponse]:
    """Retrieve chronologically ordered verification decisions and freshness checks."""
    return JobService.get_verification_history(db=db, job_id=job_id)


@jobs_router.post(
    "/{job_id}/verifications",
    response_model=JobDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit verification evidence and evaluation",
)
def submit_verification_evidence(
    job_id: uuid.UUID,
    data: JobVerificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobDetailResponse:
    """Submit structured verification evidence, observed state, and rationale."""
    return JobService.submit_verification_evidence(
        db=db, user=current_user, job_id=job_id, data=data
    )


@jobs_router.post(
    "/{job_id}/recheck",
    response_model=JobRecheckResponse,
    summary="Trigger safe availability recheck for a job listing",
)
def recheck_job(
    job_id: uuid.UUID,
    request: Optional[JobRecheckRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobRecheckResponse:
    """Safely check job target URL availability with SSRF protection."""
    req = request or JobRecheckRequest()
    return JobService.recheck_job(db=db, user=current_user, job_id=job_id, request=req)


@jobs_router.post(
    "/{job_id}/sources",
    response_model=JobSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a provenance citation to a job",
)
def add_job_source(
    job_id: uuid.UUID,
    data: JobSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> JobSourceResponse:
    """Add a new discovery source or verification citation."""
    return JobService.add_source(db=db, user=current_user, job_id=job_id, data=data)


@jobs_router.delete(
    "/{job_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job provenance source",
)
def delete_job_source(
    job_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove a provenance citation from a job listing."""
    JobService.delete_source(db=db, user=current_user, job_id=job_id, source_id=source_id)


@jobs_router.post(
    "/ingest/feed",
    response_model=FeedIngestResult,
    summary="Batch ingest structured job opportunities from a permitted feed",
)
def ingest_feed(
    data: FeedIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FeedIngestResult:
    """Batch-ingest job opportunities from a permitted feed with idempotency and error tracking."""
    return JobService.ingest_feed(db=db, user=current_user, data=data)
