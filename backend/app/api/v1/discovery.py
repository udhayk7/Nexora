import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.discovery import (
    DiscoveryBatchScanResult,
    DiscoveryOverviewResponse,
    DiscoveryScanResult,
    DiscoverySourceCreate,
    DiscoverySourceResponse,
    DiscoverySourceTestRequest,
    DiscoverySourceTestResponse,
    DiscoverySourceUpdate,
)
from app.services.discovery.adapters.registry import list_supported_adapters
from app.services.discovery.discovery_service import JobDiscoveryService

router = APIRouter()


@router.get(
    "/overview",
    response_model=DiscoveryOverviewResponse,
    summary="Get automated discovery overview statistics",
)
def get_discovery_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoveryOverviewResponse:
    """Retrieve high-level overview metrics across all configured discovery sources."""
    return JobDiscoveryService.get_overview(db)


@router.get(
    "/adapters",
    response_model=list[dict[str, str]],
    summary="List available source adapters",
)
def get_supported_adapters(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    """List all supported automated job board adapters and their configuration requirements."""
    return list_supported_adapters()


@router.get(
    "/sources",
    response_model=dict,
    summary="List configured company discovery sources",
)
def list_discovery_sources(
    company_id: Optional[uuid.UUID] = Query(None, description="Filter by company ID"),
    adapter_name: Optional[str] = Query(None, description="Filter by adapter name"),
    is_enabled: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all company sources configured for automated discovery."""
    items, total = JobDiscoveryService.list_sources(
        db=db,
        company_id=company_id,
        adapter_name=adapter_name,
        is_enabled=is_enabled,
        skip=skip,
        limit=limit,
    )
    return {"items": [i.model_dump() for i in items], "total": total, "skip": skip, "limit": limit}


@router.post(
    "/sources",
    response_model=DiscoverySourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new automated discovery source",
)
def create_discovery_source(
    payload: DiscoverySourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoverySourceResponse:
    """Register an automated discovery source (Greenhouse, Lever, Ashby, RSS, JSON)."""
    return JobDiscoveryService.create_source(db=db, user=current_user, data=payload)


@router.get(
    "/sources/{source_id}",
    response_model=DiscoverySourceResponse,
    summary="Get discovery source details",
)
def get_discovery_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoverySourceResponse:
    """Fetch details and current status for a single discovery source."""
    return JobDiscoveryService.get_source_detail(db=db, source_id=source_id)


@router.put(
    "/sources/{source_id}",
    response_model=DiscoverySourceResponse,
    summary="Update discovery source configuration",
)
def update_discovery_source(
    source_id: uuid.UUID,
    payload: DiscoverySourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoverySourceResponse:
    """Update settings, board tokens, or enabled status for a discovery source."""
    return JobDiscoveryService.update_source(
        db=db, user=current_user, source_id=source_id, data=payload
    )


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete discovery source",
)
def delete_discovery_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a discovery source configuration and its historical scan logs."""
    JobDiscoveryService.delete_source(db=db, user=current_user, source_id=source_id)


@router.post(
    "/sources/test",
    response_model=DiscoverySourceTestResponse,
    summary="Test source adapter connectivity and preview opportunities",
)
def test_discovery_source(
    payload: DiscoverySourceTestRequest,
    current_user: User = Depends(get_current_user),
) -> DiscoverySourceTestResponse:
    """Test connection to an ATS or feed without saving, returning job count and samples."""
    return JobDiscoveryService.test_source(payload)


@router.post(
    "/sources/{source_id}/scan",
    response_model=DiscoveryScanResult,
    summary="Trigger immediate manual scan for a source",
)
def scan_discovery_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoveryScanResult:
    """Immediately trigger an automated scan for a single company source."""
    return JobDiscoveryService.scan_source(
        db=db,
        source_id=source_id,
        user_id=current_user.id,
        scan_type="manual",
    )


@router.post(
    "/sources/scan-all",
    response_model=DiscoveryBatchScanResult,
    summary="Trigger batch scan for all enabled discovery sources",
)
def scan_all_discovery_sources(
    only_due: bool = Query(False, description="Scan only sources due based on frequency"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoveryBatchScanResult:
    """Trigger a batch scan across enabled company sources with failure isolation."""
    return JobDiscoveryService.scan_all_sources(
        db=db,
        only_due=only_due,
        user_id=current_user.id,
    )


@router.get(
    "/logs",
    response_model=dict,
    summary="List discovery scan audit history logs",
)
def list_discovery_logs(
    source_id: Optional[uuid.UUID] = Query(None, description="Filter by source ID"),
    company_id: Optional[uuid.UUID] = Query(None, description="Filter by company ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retrieve audit history logs of automated and manual discovery scans."""
    items, total = JobDiscoveryService.get_scan_logs(
        db=db,
        source_id=source_id,
        company_id=company_id,
        limit=limit,
        skip=skip,
    )
    return {"items": [i.model_dump() for i in items], "total": total, "skip": skip, "limit": limit}
