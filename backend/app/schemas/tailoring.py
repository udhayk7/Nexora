import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.job import JobResponse


class JobRequirementAnalysis(BaseModel):
    """
    Grounded job requirements analysis comparing job requirements against resume evidence.
    Never fabricates or converts missing requirements into claimed qualifications.
    """

    relevant_skills: list[str] = Field(
        default_factory=list,
        description="Skills supported by candidate resume that match job requirements",
    )
    relevant_experience: list[str] = Field(
        default_factory=list,
        description="Specific projects, employment, or academic experiences relevant to the role",
    )
    missing_requirements: list[str] = Field(
        default_factory=list,
        description="Job requirements not found or unevidenced in candidate's parsed resume",
    )
    keyword_opportunities: list[str] = Field(
        default_factory=list,
        description="Truthful terminology supported by candidate experience but missing in resume",
    )
    improvement_opportunities: list[str] = Field(
        default_factory=list,
        description="Suggestions for improving clarity, structure, wording, and relevance",
    )
    summary_notes: Optional[str] = Field(
        default=None,
        description="High-level alignment summary notes",
    )


class ProposedChange(BaseModel):
    """Structured AI-generated modification grounded in candidate resume evidence."""

    section_name: str = Field(
        ...,
        description="Target resume section (e.g., 'summary', 'skills', 'experience', 'projects')",
    )
    change_type: Literal[
        "wording_improvement",
        "restructuring",
        "relevance_improvement",
        "keyword_alignment",
    ] = Field(..., description="Classification of modification")
    original_content: str = Field(
        ...,
        description="Original text or bullet point from current resume",
    )
    proposed_content: str = Field(
        ...,
        description="Tailored text with enhanced professional phrasing while preserving truth",
    )
    reason: str = Field(
        ...,
        description="Detailed explanation of why this modification enhances job alignment",
    )
    supporting_evidence: Optional[dict[str, Any]] = Field(
        default=None,
        description="Supporting section and excerpt from original resume providing proof",
    )
    related_job_requirement: str = Field(
        ...,
        description="The specific job requisition criterion or skill this change targets",
    )
    confidence_level: Literal["high", "medium", "low"] = Field(
        default="high",
        description="Heuristic confidence of grounding and relevance",
    )


class TailoringChangeResponse(BaseModel):
    """Response representing an individual proposed or approved tailoring change."""

    id: uuid.UUID
    session_id: uuid.UUID
    section_name: str
    change_type: str
    original_content: str
    proposed_content: str
    user_content: Optional[str] = None
    active_content: str = Field(
        ...,
        description="Resolved text based on status (user_content, proposed, or original)",
    )
    reason: str
    supporting_evidence: Optional[dict[str, Any]] = None
    related_job_requirement: str
    confidence_level: str
    status: Literal["pending", "accepted", "rejected", "modified"]
    order_index: int
    created_at: datetime
    updated_at: datetime


class TailoringSessionCreateRequest(BaseModel):
    """Initiate a job-specific tailoring session."""

    resume_id: uuid.UUID
    version_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Resume version to base tailoring on (defaults to latest version)",
    )
    job_id: uuid.UUID


class TailoringSessionResponse(BaseModel):
    """Comprehensive tailoring session state including analysis, changes, and active LaTeX."""

    id: uuid.UUID
    user_id: uuid.UUID
    resume_id: uuid.UUID
    version_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    job_analysis: Optional[JobRequirementAnalysis] = None
    latex_content: Optional[str] = None
    tailored_version_id: Optional[uuid.UUID] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    error_summary: Optional[str] = None
    changes: list[TailoringChangeResponse] = Field(default_factory=list)
    job: Optional[JobResponse] = None
    resume_title: Optional[str] = None
    parent_version_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class TailoringSessionSummaryResponse(BaseModel):
    """Lightweight session record for history listings."""

    id: uuid.UUID
    resume_id: uuid.UUID
    version_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    job_title: str
    company_name: str
    resume_title: str
    tailored_version_id: Optional[uuid.UUID] = None
    total_changes: int = 0
    accepted_changes: int = 0
    created_at: datetime
    updated_at: datetime


class ChangeStatusUpdateRequest(BaseModel):
    """Accept, reject, or manually modify a proposed change."""

    status: Literal["pending", "accepted", "rejected", "modified"]
    user_content: Optional[str] = Field(
        default=None,
        description="Manual text override when status is 'modified' or edited",
    )


class BatchChangeActionRequest(BaseModel):
    """Batch approve all suggestions or restore original content."""

    action: Literal["accept_all", "reject_all", "restore_original"]


class UpdateContentRequest(BaseModel):
    """Save user edits to the active LaTeX or structured content."""

    latex_content: str = Field(..., description="Active LaTeX resume document content")


class SaveTailoredVersionRequest(BaseModel):
    """Finalize tailoring and persist as an immutable tailored ResumeVersion."""

    title: Optional[str] = Field(
        default=None,
        description="Optional title override for the tailored version (e.g. 'Backend Engineer')",
    )
    latex_content: Optional[str] = Field(
        default=None,
        description="Optional latest LaTeX content to commit if unsaved",
    )


class CompilePDFRequest(BaseModel):
    """Request compilation of LaTeX source to PDF with security sandboxing."""

    latex_content: Optional[str] = Field(
        default=None,
        description="LaTeX source to compile; uses session content if omitted",
    )


class CompilePDFResponse(BaseModel):
    """Result of secure PDF compilation."""

    success: bool
    compilation_engine: str = Field(
        ...,
        description="'pdflatex' (sandboxed TeX engine) or 'structured_layout_renderer'",
    )
    download_url: Optional[str] = None
    error_log: Optional[str] = None
    page_count: int = 1
    disclaimer: str = Field(
        default="PDF generated with sandbox controls. No untrusted shell execution permitted.",
    )


class TailoredVersionResponse(BaseModel):
    """Immutable tailored ResumeVersion record."""

    id: uuid.UUID
    resume_id: uuid.UUID
    version_number: int
    parent_version_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    tailoring_session_id: Optional[uuid.UUID] = None
    is_tailored: bool = True
    title: Optional[str] = None
    original_filename: str
    file_type: str
    file_size: int
    parsing_status: str
    latex_source: Optional[str] = None
    pdf_storage_path: Optional[str] = None
    tailoring_metadata: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
