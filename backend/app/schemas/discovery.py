import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiscoverySourceCreate(BaseModel):
    """Payload to register a new automated discovery source for a company."""

    company_id: uuid.UUID
    source_name: str = Field(..., min_length=2, max_length=255)
    source_type: str = Field(default="careers_page", max_length=50)
    adapter_name: str = Field(..., max_length=50)
    source_url: Optional[str] = Field(None, max_length=500)
    board_token: Optional[str] = Field(None, max_length=255)
    scan_frequency_hours: int = Field(default=24, ge=1, le=168)
    is_enabled: bool = True
    metadata_json: Optional[dict[str, Any]] = None


class DiscoverySourceUpdate(BaseModel):
    """Payload to update an automated discovery source."""

    source_name: Optional[str] = Field(None, min_length=2, max_length=255)
    adapter_name: Optional[str] = Field(None, max_length=50)
    source_url: Optional[str] = Field(None, max_length=500)
    board_token: Optional[str] = Field(None, max_length=255)
    scan_frequency_hours: Optional[int] = Field(None, ge=1, le=168)
    is_enabled: Optional[bool] = None
    metadata_json: Optional[dict[str, Any]] = None


class DiscoverySourceResponse(BaseModel):
    """Representation of a company source configured for automated discovery."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    company_name: Optional[str] = None
    source_name: str
    source_type: str
    adapter_name: Optional[str] = None
    source_url: Optional[str] = None
    board_token: Optional[str] = None
    is_enabled: bool
    scan_frequency_hours: int
    last_successful_scan_at: Optional[datetime] = None
    last_scan_status: Optional[str] = None
    last_scan_message: Optional[str] = None
    jobs_discovered_count: int
    error_count: int
    first_seen_at: datetime
    last_checked_at: datetime
    created_at: datetime
    updated_at: datetime


class DiscoverySourceTestRequest(BaseModel):
    """Payload to test adapter connectivity and preview opportunities before saving."""

    adapter_name: str = Field(..., max_length=50)
    source_url: Optional[str] = Field(None, max_length=500)
    board_token: Optional[str] = Field(None, max_length=255)


class DiscoverySourceTestResponse(BaseModel):
    """Connectivity and listing preview results from an adapter test."""

    is_success: bool
    message: str
    jobs_detected: int
    sample_jobs: list[dict[str, Any]] = []


class DiscoveryScanResult(BaseModel):
    """Results from an individual source discovery scan execution."""

    source_id: uuid.UUID
    company_name: str
    adapter_name: str
    status: str  # "success", "failed", "partial"
    jobs_found: int
    jobs_imported: int
    jobs_updated: int
    message: str
    duration_seconds: float


class DiscoveryBatchScanResult(BaseModel):
    """Aggregate results from a batch discovery run across all due or enabled sources."""

    sources_scanned: int
    total_jobs_found: int
    total_jobs_imported: int
    total_jobs_updated: int
    failed_sources: int
    results: list[DiscoveryScanResult]


class DiscoveryScanLogResponse(BaseModel):
    """Audit log item representing a discovery scan execution."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_source_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    company_name: Optional[str] = None
    adapter_name: str
    scan_type: str
    status: str
    jobs_found: int
    jobs_imported: int
    jobs_updated: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metadata_json: dict[str, Any] = {}


class DiscoveryOverviewResponse(BaseModel):
    """High-level KPI statistics for the Job Discovery workspace."""

    total_sources: int
    total_active_sources: int
    sources_scanned: int
    new_jobs_discovered: int
    updated_jobs: int
    failed_source_scans: int
    last_discovery_run: Optional[datetime] = None
    supported_adapters: list[dict[str, str]]
