import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.url_validator import validate_safe_url
from app.schemas.company import CompanyResponse

WorkArrangementType = Literal["onsite", "hybrid", "remote", "unspecified"]
JobStatusType = Literal["active", "expired", "closed", "suspicious"]
JobVerificationStatusType = Literal[
    "verified", "corroborated", "unverified", "expired", "suspicious"
]
JobFreshnessType = Literal["recent", "due_for_review", "stale", "unknown"]
JobVerificationType = Literal["system", "user"]
JobEvidenceType = Literal[
    "careers_page",
    "permitted_api",
    "announcement",
    "user_evidence",
    "other",
]
JobObservedStatusType = Literal["active", "closed", "removed", "expired", "unknown"]
JobSourceTypeLiteral = Literal[
    "careers_page",
    "official_api",
    "permitted_feed",
    "user_added",
    "curated_record",
    "other",
]


class JobSourceBase(BaseModel):
    """Base schema for provenance source citation."""

    source_name: str = Field(..., min_length=2, max_length=255)
    source_type: JobSourceTypeLiteral = Field(default="user_added")
    source_url: Optional[str] = Field(default=None, max_length=500)
    external_id: Optional[str] = Field(default=None, max_length=255)
    evidence_summary: Optional[str] = Field(default=None, max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Source URL")


class JobSourceCreate(JobSourceBase):
    """Payload to create a provenance citation."""

    pass


class JobSourceResponse(JobSourceBase):
    """Response representation of a job source."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class JobBase(BaseModel):
    """Core job listing fields."""

    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=10, max_length=50000)
    company_id: Optional[uuid.UUID] = None
    company_name: Optional[str] = Field(
        default=None,
        description="Optional company name hint for automatic association during ingestion",
    )
    employment_type: Optional[str] = Field(default=None, max_length=50)
    seniority_level: Optional[str] = Field(default=None, max_length=50)
    work_arrangement: WorkArrangementType = Field(default="unspecified")
    location_text: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state_province: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    remote_eligibility_regions: list[str] = Field(default_factory=list)
    skills_tags: list[str] = Field(default_factory=list)
    role_family: Optional[str] = Field(default=None, max_length=100)

    # Strictly explicit salary figures - never inferred or assumed
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = Field(default=None, max_length=10)
    salary_period: Optional[str] = Field(default=None, max_length=20)

    job_url: str = Field(..., max_length=500)
    application_url: Optional[str] = Field(default=None, max_length=500)
    external_source_id: Optional[str] = Field(default=None, max_length=255)
    source_published_at: Optional[datetime] = None

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, v: str) -> str:
        safe = validate_safe_url(v, field_name="Job URL")
        if not safe:
            raise ValueError("Job URL cannot be empty")
        return safe

    @field_validator("application_url")
    @classmethod
    def validate_app_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Application URL")


class JobCreate(JobBase):
    """Payload to create or ingest a single job."""

    initial_source: Optional[JobSourceCreate] = None


class JobUpdate(BaseModel):
    """Payload to update an existing job record."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, min_length=10, max_length=50000)
    company_id: Optional[uuid.UUID] = None
    employment_type: Optional[str] = Field(default=None, max_length=50)
    seniority_level: Optional[str] = Field(default=None, max_length=50)
    work_arrangement: Optional[WorkArrangementType] = None
    location_text: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state_province: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    remote_eligibility_regions: Optional[list[str]] = None
    skills_tags: Optional[list[str]] = None
    role_family: Optional[str] = Field(default=None, max_length=100)
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = Field(default=None, max_length=10)
    salary_period: Optional[str] = Field(default=None, max_length=20)
    job_url: Optional[str] = Field(default=None, max_length=500)
    application_url: Optional[str] = Field(default=None, max_length=500)
    job_status: Optional[JobStatusType] = None

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Job URL")

    @field_validator("application_url")
    @classmethod
    def validate_app_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Application URL")


class JobVerifyRequest(BaseModel):
    """Payload to update verification or active state with required evidence notes."""

    verification_status: Optional[JobVerificationStatusType] = None
    job_status: Optional[JobStatusType] = None
    verification_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory evidence rationale supporting status transition",
    )


class JobVerificationBase(BaseModel):
    """Base schema for an immutable verification check or evidence review."""

    evidence_type: JobEvidenceType = Field(default="user_evidence")
    evidence_url: Optional[str] = Field(default=None, max_length=500)
    evidence_summary: Optional[str] = Field(default=None, max_length=2000)
    observed_status: JobObservedStatusType = Field(default="active")
    verification_outcome: JobVerificationStatusType = Field(default="verified")
    reason: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory evidence rationale explaining the verification decision",
    )
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Evidence URL")


class JobVerificationCreate(JobVerificationBase):
    """Payload to submit verification evidence and status evaluation."""

    pass


class JobVerificationResponse(JobVerificationBase):
    """Immutable audit record of a completed verification check."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    verifier_type: JobVerificationType
    verifier_user_id: Optional[uuid.UUID] = None
    checked_at: datetime
    created_at: datetime


class JobRecheckRequest(BaseModel):
    """Payload to request an automated or manual recheck of job listing availability."""

    evidence_summary: Optional[str] = Field(default=None, max_length=2000)
    force_remote_check: bool = Field(default=True)


class JobRecheckResponse(BaseModel):
    """Outcome of a job listing freshness recheck."""

    job_id: uuid.UUID
    recheck_status: Literal["completed", "manual_evidence_required", "failed"]
    observed_status: JobObservedStatusType
    freshness: JobFreshnessType
    status_code: Optional[int] = None
    message: str
    verification: Optional[JobVerificationResponse] = None


class JobResponse(JobBase):
    """Standard job response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    normalized_title: str
    canonical_url_hash: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    last_checked_at: datetime
    freshness: JobFreshnessType = "unknown"
    job_status: JobStatusType
    verification_status: JobVerificationStatusType
    verification_notes: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    created_by_user_id: Optional[uuid.UUID] = None
    is_global: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    sources_count: int = 0
    company: Optional[CompanyResponse] = None


class JobDetailResponse(JobResponse):
    """Detailed job response including all provenance source records and verification history."""

    sources: list[JobSourceResponse] = Field(default_factory=list)
    verification_history: list[JobVerificationResponse] = Field(default_factory=list)


class JobDuplicateMatch(BaseModel):
    """Candidate duplicate match item."""

    job: JobResponse
    confidence: Literal["high", "medium"]
    reason: str


class JobDuplicateCheckResponse(BaseModel):
    """Duplicate detection evaluation response."""

    matches: list[JobDuplicateMatch] = Field(default_factory=list)


class JobListResponse(BaseModel):
    """Paginated list of job records."""

    items: list[JobResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class FeedIngestRequest(BaseModel):
    """Payload to ingest structured job records from a permitted feed or dataset."""

    feed_name: str = Field(..., min_length=2, max_length=255)
    source_type: JobSourceTypeLiteral = Field(default="permitted_feed")
    source_url: Optional[str] = Field(default=None, max_length=500)
    records: list[JobCreate] = Field(..., min_length=1, max_length=500)

    @field_validator("source_url")
    @classmethod
    def validate_feed_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Feed Source URL")


class FeedIngestResult(BaseModel):
    """Summary of batch ingestion processing."""

    feed_name: str
    total_processed: int
    created_count: int
    updated_count: int
    errors_count: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
