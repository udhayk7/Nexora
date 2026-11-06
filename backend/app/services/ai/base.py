from dataclasses import dataclass
from typing import Any, Optional, Protocol

from app.core.errors import AppError
from app.schemas.analysis import ResumeAnalysisResult


class AIProviderError(AppError):
    """Base exception for AI provider operations."""

    def __init__(
        self,
        message: str = "AI analysis failed",
        code: str = "AI_PROVIDER_ERROR",
        status_code: int = 502,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code)


class AIConfigurationError(AIProviderError):
    """Exception when required AI provider credentials or model settings are missing."""

    def __init__(self, message: str = "AI provider is not configured") -> None:
        super().__init__(message=message, code="AI_CONFIG_ERROR", status_code=503)


class AITimeoutError(AIProviderError):
    """Exception when AI provider request times out."""

    def __init__(self, message: str = "AI provider request timed out") -> None:
        super().__init__(message=message, code="AI_TIMEOUT_ERROR", status_code=504)


class AIRateLimitError(AIProviderError):
    """Exception when AI provider rate limits or quotas are exceeded."""

    def __init__(
        self,
        message: str = "AI provider rate limit reached. Please try again later.",
    ) -> None:
        super().__init__(message=message, code="AI_RATE_LIMIT_ERROR", status_code=429)


@dataclass
class AIProviderResponse:
    """Standardized response from any AI provider."""

    result: ResumeAnalysisResult
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class AIProvider(Protocol):
    """Protocol for AI analysis providers."""

    name: str
    model_name: str

    @property
    def is_configured(self) -> bool: ...

    def analyze_resume(
        self,
        resume_text: str,
        structured_sections: Optional[dict[str, Any]] = None,
    ) -> AIProviderResponse:
        """Analyze resume text and return structured, evidence-grounded result."""
        ...
