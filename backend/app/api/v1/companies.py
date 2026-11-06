import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.company import (
    CompanyCategoryType,
    CompanyCreate,
    CompanyDetailResponse,
    CompanyDuplicateCheckResponse,
    CompanyListResponse,
    CompanyMergeRequest,
    CompanySourceCreate,
    CompanySourceResponse,
    CompanySourceUpdate,
    CompanyUpdate,
    CompanyVerifyRequest,
    VerificationStatusType,
)
from app.services.company_service import CompanyService

companies_router = APIRouter(prefix="/companies", tags=["companies"])


@companies_router.get(
    "",
    response_model=CompanyListResponse,
    summary="List and filter discovery companies",
)
def list_companies(
    search: Optional[str] = Query(None, description="Search term across name, domain, and desc"),
    category: Optional[CompanyCategoryType] = Query(None, description="Filter by company category"),
    verification_status: Optional[VerificationStatusType] = Query(
        None, description="Filter by status"
    ),
    industry: Optional[str] = Query(None, description="Filter by industry tag"),
    technology: Optional[str] = Query(None, description="Filter by tech stack tag"),
    region: Optional[str] = Query(None, description="Filter by country or operating region"),
    user_only: bool = Query(False, description="Filter to only records added by current user"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyListResponse:
    """Retrieve paginated companies matching search and criteria."""
    return CompanyService.list_companies(
        db=db,
        search=search,
        category=category,
        verification_status=verification_status,
        industry=industry,
        technology=technology,
        region=region,
        user_only=user_only,
        current_user=current_user,
        page=page,
        per_page=per_page,
    )


@companies_router.get(
    "/duplicates/check",
    response_model=CompanyDuplicateCheckResponse,
    summary="Check for potential duplicate companies",
)
def check_duplicates(
    name: str = Query(..., min_length=1, description="Company name to check"),
    website_url: Optional[str] = Query(None, description="Optional website to match by domain"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> CompanyDuplicateCheckResponse:
    """Detect matching existing company records by normalized name or domain."""
    return CompanyService.check_duplicates(db=db, name=name, website_url=website_url)


@companies_router.post(
    "",
    response_model=CompanyDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company",
)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyDetailResponse:
    """Register a new company record with optional initial discovery source."""
    return CompanyService.create_company(db=db, user=current_user, data=data)


@companies_router.get(
    "/{company_id}",
    response_model=CompanyDetailResponse,
    summary="Get detailed company profile and sources",
)
def get_company_detail(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> CompanyDetailResponse:
    """Retrieve full company details, tags, and provenance sources."""
    return CompanyService.get_company_detail(db=db, company_id=company_id)


@companies_router.patch(
    "/{company_id}",
    response_model=CompanyDetailResponse,
    summary="Update company details",
)
def update_company(
    company_id: uuid.UUID,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyDetailResponse:
    """Update company metadata with authorization enforcement."""
    return CompanyService.update_company(db=db, user=current_user, company_id=company_id, data=data)


@companies_router.post(
    "/{company_id}/verify",
    response_model=CompanyDetailResponse,
    summary="Update company verification status",
)
def verify_company(
    company_id: uuid.UUID,
    data: CompanyVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyDetailResponse:
    """Transition company verification status with mandatory evidence notes."""
    return CompanyService.verify_company(db=db, user=current_user, company_id=company_id, data=data)


@companies_router.post(
    "/{company_id}/sources",
    response_model=CompanySourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a discovery source",
)
def add_company_source(
    company_id: uuid.UUID,
    data: CompanySourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanySourceResponse:
    """Add a new discovery or verification provenance source."""
    return CompanyService.add_source(db=db, user=current_user, company_id=company_id, data=data)


@companies_router.patch(
    "/{company_id}/sources/{source_id}",
    response_model=CompanySourceResponse,
    summary="Update a discovery source",
)
def update_company_source(
    company_id: uuid.UUID,
    source_id: uuid.UUID,
    data: CompanySourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanySourceResponse:
    """Update provenance source details."""
    return CompanyService.update_source(
        db=db, user=current_user, company_id=company_id, source_id=source_id, data=data
    )


@companies_router.delete(
    "/{company_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a discovery source",
)
def delete_company_source(
    company_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove a discovery provenance source from a company."""
    CompanyService.delete_source(
        db=db, user=current_user, company_id=company_id, source_id=source_id
    )


@companies_router.post(
    "/{company_id}/merge",
    response_model=CompanyDetailResponse,
    summary="Explicitly merge a duplicate company",
)
def merge_companies(
    company_id: uuid.UUID,
    data: CompanyMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyDetailResponse:
    """Explicitly merge a secondary duplicate company into this target company."""
    return CompanyService.merge_companies(
        db=db,
        user=current_user,
        target_company_id=company_id,
        secondary_company_id=data.secondary_company_id,
        merge_reason=data.merge_reason,
    )
