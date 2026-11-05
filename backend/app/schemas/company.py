import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.url_validator import validate_safe_url

CompanyCategoryType = Literal[
    "product_company",
    "mnc",
    "gcc",
    "big_four",
    "large_it_services",
    "established_startup",
    "other",
]

VerificationStatusType = Literal[
    "verified",
    "corroborated",
    "unverified",
    "suspicious",
]

SourceTypeLiteral = Literal[
    "official_website",
    "careers_page",
    "public_directory",
    "user_added",
    "curated_dataset",
    "other",
]


class CompanySourceBase(BaseModel):
    """Base discovery source schema."""

    source_name: str = Field(..., min_length=2, max_length=255)
    source_type: SourceTypeLiteral = Field(default="user_added")
    source_url: Optional[str] = Field(default=None, max_length=500)
    evidence_summary: Optional[str] = Field(default=None, max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Source URL")


class CompanySourceCreate(CompanySourceBase):
    """Payload to add a new discovery source."""

    pass


class CompanySourceUpdate(BaseModel):
    """Payload to update an existing discovery source."""

    source_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    source_type: Optional[SourceTypeLiteral] = None
    source_url: Optional[str] = Field(default=None, max_length=500)
    evidence_summary: Optional[str] = Field(default=None, max_length=2000)
    metadata_json: Optional[dict[str, Any]] = None

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Source URL")


class CompanySourceResponse(CompanySourceBase):
    """Response representation of a company source."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    first_seen_at: datetime
    last_checked_at: datetime
    created_at: datetime
    updated_at: datetime


class CompanyBase(BaseModel):
    """Base company information."""

    name: str = Field(..., min_length=1, max_length=255)
    category: CompanyCategoryType = Field(default="other")
    website_url: Optional[str] = Field(default=None, max_length=500)
    careers_url: Optional[str] = Field(default=None, max_length=500)
    headquarters_country: Optional[str] = Field(default=None, max_length=100)
    headquarters_city: Optional[str] = Field(default=None, max_length=100)
    operating_regions: list[str] = Field(default_factory=list)
    industry_tags: list[str] = Field(default_factory=list)
    technology_tags: list[str] = Field(default_factory=list)
    size_band: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=5000)
    primary_source: Optional[str] = Field(default=None, max_length=100)
    primary_source_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Website URL")

    @field_validator("careers_url")
    @classmethod
    def validate_careers(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Careers URL")


class CompanyCreate(CompanyBase):
    """Payload to register a new company."""

    initial_source: Optional[CompanySourceCreate] = None


class CompanyUpdate(BaseModel):
    """Payload to update an existing company."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[CompanyCategoryType] = None
    website_url: Optional[str] = Field(default=None, max_length=500)
    careers_url: Optional[str] = Field(default=None, max_length=500)
    headquarters_country: Optional[str] = Field(default=None, max_length=100)
    headquarters_city: Optional[str] = Field(default=None, max_length=100)
    operating_regions: Optional[list[str]] = None
    industry_tags: Optional[list[str]] = None
    technology_tags: Optional[list[str]] = None
    size_band: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=5000)
    primary_source: Optional[str] = Field(default=None, max_length=100)
    primary_source_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Website URL")

    @field_validator("careers_url")
    @classmethod
    def validate_careers(cls, v: Optional[str]) -> Optional[str]:
        return validate_safe_url(v, field_name="Careers URL")


class CompanyVerifyRequest(BaseModel):
    """Payload to update verification status with mandatory evidence notes."""

    verification_status: VerificationStatusType
    verification_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Reasoning or evidence supporting verification transition",
    )
    source_id: Optional[uuid.UUID] = None


class CompanyMergeRequest(BaseModel):
    """Payload to explicitly merge a secondary duplicate company into this target company."""

    secondary_company_id: uuid.UUID
    merge_reason: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Explicit auditable justification for merging records",
    )


class CompanyResponse(CompanyBase):
    """Standard company response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    normalized_name: str
    normalized_domain: Optional[str] = None
    verification_status: VerificationStatusType
    verification_notes: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    created_by_user_id: Optional[uuid.UUID] = None
    is_global: bool
    is_merged: bool
    merged_into_company_id: Optional[uuid.UUID] = None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    sources_count: int = 0


class CompanyDetailResponse(CompanyResponse):
    """Detailed company representation including full provenance sources."""

    sources: list[CompanySourceResponse] = Field(default_factory=list)


class CompanyDuplicateMatch(BaseModel):
    """Potential duplicate match item."""

    company: CompanyResponse
    confidence: Literal["high", "medium"]
    reason: str


class CompanyDuplicateCheckResponse(BaseModel):
    """Duplicate detection evaluation response."""

    normalized_name: str
    normalized_domain: Optional[str] = None
    matches: list[CompanyDuplicateMatch] = Field(default_factory=list)


class CompanyListResponse(BaseModel):
    """Paginated list of company records."""

    items: list[CompanyResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
