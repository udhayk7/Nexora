"""Pydantic schemas package."""

from app.schemas.health import HealthResponse
from app.schemas.tailoring import (
    BatchChangeActionRequest,
    ChangeStatusUpdateRequest,
    CompilePDFRequest,
    CompilePDFResponse,
    JobRequirementAnalysis,
    ProposedChange,
    SaveTailoredVersionRequest,
    TailoredVersionResponse,
    TailoringChangeResponse,
    TailoringSessionCreateRequest,
    TailoringSessionResponse,
    TailoringSessionSummaryResponse,
    UpdateContentRequest,
)

__all__ = [
    "HealthResponse",
    "JobRequirementAnalysis",
    "ProposedChange",
    "TailoringChangeResponse",
    "TailoringSessionCreateRequest",
    "TailoringSessionResponse",
    "TailoringSessionSummaryResponse",
    "ChangeStatusUpdateRequest",
    "BatchChangeActionRequest",
    "UpdateContentRequest",
    "SaveTailoredVersionRequest",
    "CompilePDFRequest",
    "CompilePDFResponse",
    "TailoredVersionResponse",
]

