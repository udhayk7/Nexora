import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ParsedContactSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: list[str] = Field(default_factory=list)


class ParsedExperienceSchema(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    date_range: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class ParsedEducationSchema(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[str] = None
    details: list[str] = Field(default_factory=list)


class ResumeParsedProfileSchema(BaseModel):
    contact: ParsedContactSchema = Field(default_factory=ParsedContactSchema)
    summary: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ParsedExperienceSchema] = Field(default_factory=list)
    education: list[ParsedEducationSchema] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ResumeVersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    original_filename: str
    file_type: str
    file_size: int
    parsing_status: str
    error_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeVersionDetail(ResumeVersionSummary):
    parsed_content: Optional[dict[str, Any]] = None
    raw_text: Optional[str] = None

    model_config = {"from_attributes": True}


class ResumeSummaryResponse(BaseModel):
    id: uuid.UUID
    title: str
    current_version_id: Optional[uuid.UUID] = None
    current_version_number: Optional[int] = None
    parsing_status: str
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    version_count: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    current_version_id: Optional[uuid.UUID] = None
    current_version: Optional[ResumeVersionDetail] = None
    versions: list[ResumeVersionSummary] = Field(default_factory=list)
    version_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeUpdateTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

