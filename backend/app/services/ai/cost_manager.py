import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.ai_usage import AIUsageLog
from app.schemas.ai_usage import (
    AICostCheckResult,
    AIProviderSpendBreakdown,
    AIUsageRecord,
    AIUsageSummaryResponse,
)


class AICostManager:
    """Centralized AI usage monitoring, budget limits enforcement, and response caching."""

    @classmethod
    def compute_request_hash(cls, provider: str, model: str, prompt: str, **kwargs: Any) -> str:
        """Generate a SHA-256 fingerprint for duplicate detection and caching."""
        payload = f"{provider}:{model}:{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def check_limits_and_cache(
        cls,
        db: Session,
        user_id: Optional[uuid.UUID] = None,
        feature: str = "general",
        request_hash: Optional[str] = None,
    ) -> AICostCheckResult:
        """Enforces server-side daily/monthly spending and token limits, checks cache."""
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # 1. Check Platform Daily Spending Limit
        daily_spend = (
            db.query(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0))
            .filter(AIUsageLog.created_at >= today_start)
            .scalar()
            or 0.0
        )
        if daily_spend >= settings.AI_DAILY_BUDGET_USD:
            logger.warning(
                "AI daily spending limit exceeded: $%.4f / $%.2f",
                daily_spend,
                settings.AI_DAILY_BUDGET_USD,
            )
            return AICostCheckResult(
                allowed=False,
                reason=(
                    f"Platform daily AI spending limit exceeded (${daily_spend:.2f} / "
                    f"${settings.AI_DAILY_BUDGET_USD:.2f}). Please try again tomorrow."
                ),
            )

        # 2. Check Platform Monthly Spending Limit
        monthly_spend = (
            db.query(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0))
            .filter(AIUsageLog.created_at >= month_start)
            .scalar()
            or 0.0
        )
        if monthly_spend >= settings.AI_MONTHLY_BUDGET_USD:
            logger.warning(
                "AI monthly spending limit exceeded: $%.4f / $%.2f",
                monthly_spend,
                settings.AI_MONTHLY_BUDGET_USD,
            )
            return AICostCheckResult(
                allowed=False,
                reason=(
                    f"Platform monthly AI spending limit exceeded (${monthly_spend:.2f} / "
                    f"${settings.AI_MONTHLY_BUDGET_USD:.2f})."
                ),
            )

        # 3. Check Per-User Daily Token Limit
        if user_id:
            user_today_tokens = (
                db.query(func.coalesce(func.sum(AIUsageLog.total_tokens), 0))
                .filter(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= today_start)
                .scalar()
                or 0
            )
            if user_today_tokens >= settings.AI_USER_DAILY_TOKEN_LIMIT:
                return AICostCheckResult(
                    allowed=False,
                    reason=(
                        f"Personal daily AI token limit reached ({user_today_tokens:,} / "
                        f"{settings.AI_USER_DAILY_TOKEN_LIMIT:,} tokens)."
                    ),
                )

        # 4. Check Response Cache (if hash provided and caching enabled)
        if request_hash and settings.AI_ENABLE_RESPONSE_CACHE:
            cached_resp = cls._get_from_cache(request_hash)
            if cached_resp:
                return AICostCheckResult(
                    allowed=True,
                    cached_response=cached_resp,
                )

        return AICostCheckResult(allowed=True)

    @classmethod
    def record_usage(
        cls,
        db: Session,
        provider: str,
        model: str,
        feature: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        request_status: str = "success",
        latency_ms: int = 0,
        cache_hit: bool = False,
        request_hash: Optional[str] = None,
        error_message: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> AIUsageLog:
        """Persists AI request usage telemetry and audit record."""
        log = AIUsageLog(
            id=uuid.uuid4(),
            user_id=user_id,
            provider=provider,
            model=model,
            feature=feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens or (prompt_tokens + completion_tokens),
            estimated_cost_usd=round(estimated_cost_usd, 6),
            request_status=request_status,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            request_hash=request_hash,
            error_message=error_message[:500] if error_message else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @classmethod
    def get_usage_summary(
        cls,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> AIUsageSummaryResponse:
        """Aggregates platform or user-scoped AI consumption and estimated costs."""
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # Daily and monthly platform spend
        daily_spend = (
            db.query(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0))
            .filter(AIUsageLog.created_at >= today_start)
            .scalar()
            or 0.0
        )
        monthly_spend = (
            db.query(func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0.0))
            .filter(AIUsageLog.created_at >= month_start)
            .scalar()
            or 0.0
        )

        # Base query for totals
        q = db.query(AIUsageLog)
        if start_date:
            q = q.filter(AIUsageLog.created_at >= start_date)
        if end_date:
            q = q.filter(AIUsageLog.created_at <= end_date)
        if user_id:
            q = q.filter(AIUsageLog.user_id == user_id)

        all_logs = q.order_by(AIUsageLog.created_at.desc()).limit(100).all()

        total_requests = len(all_logs)
        total_prompt = sum(entry.prompt_tokens for entry in all_logs)
        total_comp = sum(entry.completion_tokens for entry in all_logs)
        total_tok = sum(entry.total_tokens for entry in all_logs)
        total_cost = sum(entry.estimated_cost_usd for entry in all_logs)

        # Group by provider
        by_provider: dict[str, AIProviderSpendBreakdown] = {}
        for entry in all_logs:
            p = entry.provider or "unknown"
            if p not in by_provider:
                by_provider[p] = AIProviderSpendBreakdown(
                    requests_count=0, total_tokens=0, estimated_cost_usd=0.0
                )
            by_provider[p].requests_count += 1
            by_provider[p].total_tokens += entry.total_tokens
            by_provider[p].estimated_cost_usd = round(
                by_provider[p].estimated_cost_usd + entry.estimated_cost_usd, 6
            )

        # Group by model
        by_model: dict[str, AIProviderSpendBreakdown] = {}
        for entry in all_logs:
            m = entry.model or "unknown"
            if m not in by_model:
                by_model[m] = AIProviderSpendBreakdown(
                    requests_count=0, total_tokens=0, estimated_cost_usd=0.0
                )
            by_model[m].requests_count += 1
            by_model[m].total_tokens += entry.total_tokens
            by_model[m].estimated_cost_usd = round(
                by_model[m].estimated_cost_usd + entry.estimated_cost_usd, 6
            )

        # Group by feature
        by_feature: dict[str, AIProviderSpendBreakdown] = {}
        for entry in all_logs:
            f = entry.feature or "general"
            if f not in by_feature:
                by_feature[f] = AIProviderSpendBreakdown(
                    requests_count=0, total_tokens=0, estimated_cost_usd=0.0
                )
            by_feature[f].requests_count += 1
            by_feature[f].total_tokens += entry.total_tokens
            by_feature[f].estimated_cost_usd = round(
                by_feature[f].estimated_cost_usd + entry.estimated_cost_usd, 6
            )

        daily_pct = round((daily_spend / max(0.01, settings.AI_DAILY_BUDGET_USD)) * 100, 1)
        monthly_pct = round((monthly_spend / max(0.01, settings.AI_MONTHLY_BUDGET_USD)) * 100, 1)

        recent_records = [AIUsageRecord.model_validate(entry) for entry in all_logs[:20]]

        return AIUsageSummaryResponse(
            total_requests=total_requests,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_comp,
            total_tokens=total_tok,
            total_estimated_cost_usd=round(total_cost, 4),
            daily_budget_usd=settings.AI_DAILY_BUDGET_USD,
            monthly_budget_usd=settings.AI_MONTHLY_BUDGET_USD,
            daily_spend_usd=round(daily_spend, 4),
            monthly_spend_usd=round(monthly_spend, 4),
            daily_budget_percent=daily_pct,
            monthly_budget_percent=monthly_pct,
            by_provider=by_provider,
            by_model=by_model,
            by_feature=by_feature,
            recent_logs=recent_records,
        )

    # -----------------------------------------------------------------------
    # In-Memory / Redis Response Cache Layer
    # -----------------------------------------------------------------------
    _in_memory_cache: dict[str, tuple[dict[str, Any], float]] = {}

    @classmethod
    def _get_from_cache(cls, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached response if within TTL."""
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            val = r.get(f"ai_cache:{cache_key}")
            if val:
                cached_json = json.loads(val)
                if isinstance(cached_json, dict):
                    return cached_json
        except Exception:
            pass

        # In-memory fallback
        item = cls._in_memory_cache.get(cache_key)
        if item:
            data, exp = item
            if time.time() < exp:
                return data
            del cls._in_memory_cache[cache_key]
        return None

    @classmethod
    def save_to_cache(cls, cache_key: str, data: dict[str, Any]) -> None:
        """Store response in cache with configured TTL."""
        ttl = settings.AI_RESPONSE_CACHE_TTL_SECONDS
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.set(f"ai_cache:{cache_key}", json.dumps(data), ex=ttl)
        except Exception:
            pass

        import time

        cls._in_memory_cache[cache_key] = (data, time.time() + ttl)
