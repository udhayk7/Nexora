import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AIUsageRecord(BaseModel):
    """Schema for individual AI usage audit log entry."""

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    provider: str
    model: str
    feature: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    request_status: str
    latency_ms: int
    cache_hit: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AIProviderSpendBreakdown(BaseModel):
    requests_count: int
    total_tokens: int
    estimated_cost_usd: float


class AIUsageSummaryResponse(BaseModel):
    """Aggregated AI consumption and cost monitoring overview."""

    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float

    # Budget limits & tracking
    daily_budget_usd: float
    monthly_budget_usd: float
    daily_spend_usd: float
    monthly_spend_usd: float
    daily_budget_percent: float
    monthly_budget_percent: float

    # Breakdowns
    by_provider: dict[str, AIProviderSpendBreakdown]
    by_model: dict[str, AIProviderSpendBreakdown]
    by_feature: dict[str, AIProviderSpendBreakdown]

    recent_logs: list[AIUsageRecord] = Field(default_factory=list)

    disclaimer: str = (
        "Estimated cost computed from token consumption and published provider rates. "
        "Actual provider invoices may vary depending on taxes, discounts, or enterprise tiers."
    )


class AICostCheckResult(BaseModel):
    """Result of server-side budget and rate limit evaluation."""

    allowed: bool
    reason: Optional[str] = None
    cached_response: Optional[dict[str, Any]] = None
