import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.services.ai.base import (
    AIConfigurationError,
)
from app.services.ai.cost_manager import AICostManager
from app.services.ai.factory import get_ai_provider
from app.services.ai.factory import test_all_ai_providers as check_all_ai_providers
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def _create_user(db: Session, email_prefix: str = "prod_user") -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Production Test User",
        hashed_password="hashed_test_password",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. AI Provider Configuration & Model Routing
# ---------------------------------------------------------------------------


def test_all_ai_providers_diagnostic():
    """Verify diagnostic provider check returns OpenAI and Gemini statuses."""
    res = check_all_ai_providers()
    assert "primary_provider" in res
    assert "openai" in res
    assert "gemini" in res


def test_openai_provider_routing_and_unconfigured():
    """Verify OpenAI provider routes tiers and handles unconfigured key safely."""
    with patch.object(settings, "OPENAI_API_KEY", None):
        prov = OpenAIProvider(api_key=None)
        assert not prov.is_configured
        status = prov.test_connection()
        assert status["status"] == "unconfigured"
        assert "OPENAI_API_KEY" in status["message"]

        with pytest.raises(AIConfigurationError):
            prov._get_client()

    prov_configured = OpenAIProvider(api_key="sk-test-mock-key")
    assert prov_configured.is_configured
    assert prov_configured.get_model_for_tier("routine") == settings.OPENAI_MODEL
    assert prov_configured.get_model_for_tier("strong") == settings.OPENAI_STRONG_MODEL


def test_gemini_provider_routing_and_unconfigured():
    """Verify Gemini provider routes tiers and handles unconfigured key safely."""
    with patch.object(settings, "GEMINI_API_KEY", None):
        prov = GeminiProvider(api_key=None)
        assert not prov.is_configured
        status = prov.test_connection()
        assert status["status"] == "unconfigured"
        assert "GEMINI_API_KEY" in status["message"]

        with pytest.raises(AIConfigurationError):
            prov._get_client()

    prov_configured = GeminiProvider(api_key="gemini-test-mock-key")
    assert prov_configured.is_configured
    assert prov_configured.get_model_for_tier("routine") == settings.GEMINI_MODEL
    assert prov_configured.get_model_for_tier("strong") == settings.GEMINI_STRONG_MODEL


def test_ai_factory_dynamic_routing_and_fallback():
    """Test dynamic routing from primary to secondary provider when primary is unconfigured."""
    # When both unconfigured, primary is returned (unconfigured)
    with (
        patch.object(settings, "OPENAI_API_KEY", None),
        patch.object(settings, "GEMINI_API_KEY", None),
    ):
        prov = get_ai_provider()
        assert prov.name == "openai"
        assert not prov.is_configured

    # When primary unconfigured but secondary has key, fall back to secondary
    with (
        patch.object(settings, "OPENAI_API_KEY", None),
        patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"),
    ):
        prov = get_ai_provider()
        assert prov.name == "gemini"
        assert prov.is_configured

    # When explicitly requesting a provider, do not switch
    with (
        patch.object(settings, "OPENAI_API_KEY", None),
        patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key"),
    ):
        prov = get_ai_provider("openai")
        assert prov.name == "openai"
        assert not prov.is_configured


def test_openai_generate_text_and_json_mocked():
    """Test live text and structured JSON responses with mocked OpenAI client."""
    prov = OpenAIProvider(api_key="mock-key")
    mock_client = MagicMock()

    # Mock text response
    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI synthesized advice"
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 25
    mock_usage.total_tokens = 75
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage = mock_usage
    mock_client.chat.completions.create.return_value = mock_resp

    with patch.object(prov, "_get_client", return_value=mock_client):
        text, telemetry = prov.generate_text("Analyze candidate career trajectory", tier="routine")
        assert text == "OpenAI synthesized advice"
        assert telemetry["total_tokens"] == 75
        assert telemetry["provider"] == "openai"
        assert telemetry["estimated_cost_usd"] > 0

    # Mock JSON response
    mock_json_choice = MagicMock()
    mock_json_choice.message.content = '{"key_skills": ["Python", "FastAPI"], "score": 92}'
    mock_json_resp = MagicMock()
    mock_json_resp.choices = [mock_json_choice]
    mock_json_resp.usage = mock_usage
    mock_client.chat.completions.create.return_value = mock_json_resp

    with patch.object(prov, "_get_client", return_value=mock_client):
        json_data, telemetry = prov.generate_json("Extract candidate competencies", tier="routine")
        assert json_data["score"] == 92
        assert "Python" in json_data["key_skills"]
        assert telemetry["provider"] == "openai"


# ---------------------------------------------------------------------------
# 2. Centralized AI Cost Management & Budget Limits
# ---------------------------------------------------------------------------


def test_ai_cost_manager_record_usage(db_session: Session):
    """Verify recording AI usage logs and computing aggregate summaries."""
    user = _create_user(db_session, "cost_user")

    log1 = AICostManager.record_usage(
        db=db_session,
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        feature="resume_analysis",
        prompt_tokens=400,
        completion_tokens=200,
        total_tokens=600,
        estimated_cost_usd=0.00018,
        request_status="success",
        latency_ms=180,
    )
    assert log1.id is not None
    assert log1.estimated_cost_usd == 0.00018

    log2 = AICostManager.record_usage(
        db=db_session,
        user_id=user.id,
        provider="gemini",
        model="gemini-2.5-flash",
        feature="cover_letter",
        prompt_tokens=500,
        completion_tokens=300,
        total_tokens=800,
        estimated_cost_usd=0.000127,
        request_status="success",
        latency_ms=210,
    )
    assert log2.id is not None

    summary = AICostManager.get_usage_summary(db=db_session, user_id=user.id)
    assert summary.total_requests >= 2
    assert summary.total_tokens >= 1400
    assert summary.total_estimated_cost_usd > 0
    assert "openai" in summary.by_provider
    assert "gemini" in summary.by_provider
    assert "resume_analysis" in summary.by_feature
    assert "Actual provider invoices may vary" in summary.disclaimer


def test_ai_cost_manager_daily_spending_limit_enforcement(db_session: Session):
    """Verify server-side daily budget enforcement when platform spending ceiling is breached."""
    user = _create_user(db_session, "budget_limit_user")

    # Record a heavy usage entry exceeding $10.00 daily budget
    AICostManager.record_usage(
        db=db_session,
        user_id=user.id,
        provider="openai",
        model="gpt-4o",
        feature="heavy_batch",
        prompt_tokens=500_000,
        completion_tokens=800_000,
        estimated_cost_usd=10.50,  # Exceeds settings.AI_DAILY_BUDGET_USD ($10.0)
        request_status="success",
    )

    result = AICostManager.check_limits_and_cache(db=db_session, user_id=user.id)
    assert not result.allowed
    assert "daily ai spending limit exceeded" in result.reason.lower()


def test_ai_cost_manager_per_user_token_limit_enforcement(db_session: Session):
    """Verify server-side enforcement of personal daily token limits."""
    user = _create_user(db_session, "user_token_user")

    with patch.object(settings, "AI_DAILY_BUDGET_USD", 500.0):  # Allow high platform budget
        AICostManager.record_usage(
            db=db_session,
            user_id=user.id,
            provider="openai",
            model="gpt-4o-mini",
            feature="loop_eval",
            total_tokens=160_000,  # Exceeds AI_USER_DAILY_TOKEN_LIMIT (150,000)
            estimated_cost_usd=0.05,
            request_status="success",
        )

        result = AICostManager.check_limits_and_cache(db=db_session, user_id=user.id)
        assert not result.allowed
        assert "token limit reached" in result.reason.lower()


def test_ai_cost_manager_request_hash_caching(db_session: Session):
    """Verify duplicate request fingerprinting and response caching."""
    h = AICostManager.compute_request_hash(
        provider="openai", model="gpt-4o-mini", prompt="Tell me about Nexora"
    )
    assert len(h) == 64

    # Save to cache
    test_data = {"advice": "Focus on clean distributed architecture."}
    AICostManager.save_to_cache(h, test_data)

    # Check cache hit
    check = AICostManager.check_limits_and_cache(db=db_session, request_hash=h)
    assert check.allowed
    assert check.cached_response is not None
    assert check.cached_response["advice"] == test_data["advice"]


# ---------------------------------------------------------------------------
# 3. Integration Health Dashboard & Diagnostic APIs
# ---------------------------------------------------------------------------


def test_integrations_health_endpoint(client: TestClient, db_session: Session):
    """Test GET /api/v1/integrations/health returns structured status across all services."""
    user = _create_user(db_session, "health_user")
    headers = _get_auth_headers(user)

    res = client.get("/api/v1/integrations/health", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "postgres" in data
    assert data["postgres"]["status"] == "connected"
    assert "pool_metrics" in data["postgres"]

    assert "redis" in data
    assert data["redis"]["status"] in ("connected", "disconnected")

    assert "celery" in data
    assert data["celery"]["service"] == "celery"

    assert "gmail" in data
    assert data["gmail"]["service"] == "gmail_oauth"

    assert "job_sources" in data
    assert data["job_sources"]["status"] == "operational"
    assert len(data["job_sources"]["adapters"]) == 5

    assert "openai" in data
    assert "gemini" in data


def test_integrations_test_service_endpoint(client: TestClient, db_session: Session):
    """Test POST /api/v1/integrations/test/{service} for postgres, redis, and job sources."""
    user = _create_user(db_session, "test_svc_user")
    headers = _get_auth_headers(user)

    # Test Postgres
    pg_res = client.post("/api/v1/integrations/test/postgres", headers=headers)
    assert pg_res.status_code == 200
    assert pg_res.json()["status"] == "connected"

    # Test Redis
    rd_res = client.post("/api/v1/integrations/test/redis", headers=headers)
    assert rd_res.status_code == 200
    assert rd_res.json()["service"] == "redis"

    # Test Celery
    cl_res = client.post("/api/v1/integrations/test/celery", headers=headers)
    assert cl_res.status_code == 200
    assert cl_res.json()["service"] == "celery"

    # Test Job Sources
    js_res = client.post("/api/v1/integrations/test/job_sources", headers=headers)
    assert js_res.status_code == 200
    assert js_res.json()["status"] == "operational"

    # Test Unknown service
    un_res = client.post("/api/v1/integrations/test/unknown_vendor", headers=headers)
    assert un_res.status_code == 200
    assert un_res.json()["status"] == "unavailable"


def test_integrations_ai_usage_endpoint(client: TestClient, db_session: Session):
    """Test GET /api/v1/integrations/ai-usage returns spending limits and telemetry."""
    user = _create_user(db_session, "usage_api_user")
    headers = _get_auth_headers(user)

    # Seed sample usage
    AICostManager.record_usage(
        db=db_session,
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        feature="interview_prep",
        prompt_tokens=100,
        completion_tokens=50,
        estimated_cost_usd=0.000045,
    )

    res = client.get("/api/v1/integrations/ai-usage", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["daily_budget_usd"] == settings.AI_DAILY_BUDGET_USD
    assert data["monthly_budget_usd"] == settings.AI_MONTHLY_BUDGET_USD
    assert data["total_requests"] >= 1
    assert "Actual provider invoices may vary" in data["disclaimer"]


def test_integrations_job_sources_endpoint(client: TestClient, db_session: Session):
    """Test GET /api/v1/integrations/job-sources documents all 5 adapters."""
    user = _create_user(db_session, "job_src_user")
    headers = _get_auth_headers(user)

    res = client.get("/api/v1/integrations/job-sources", headers=headers)
    assert res.status_code == 200
    data = res.json()
    adapters = data["adapters"]
    assert "greenhouse" in adapters
    assert "lever" in adapters
    assert "ashby" in adapters
    assert "rss_atom" in adapters
    assert "json_feed" in adapters
    # Ensure none require bypass or unauthorized scraping
    for _name, adapter in adapters.items():
        assert adapter["auth_required"] is False
        assert "rate_limit_policy" in adapter
        assert "normalization" in adapter
        assert "deduplication" in adapter


# ---------------------------------------------------------------------------
# 4. Gmail OAuth Security & Confirmation Boundary
# ---------------------------------------------------------------------------


def test_gmail_oauth_disconnected_state(client: TestClient, db_session: Session):
    """Verify disconnected user gets safe disconnected status without token exposure."""
    user = _create_user(db_session, "gmail_disco_user")
    headers = _get_auth_headers(user)

    res = client.get("/api/v1/integrations/google/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_connected"] is False
    assert data["email"] is None
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_gmail_send_strictly_requires_explicit_confirmation(
    client: TestClient, db_session: Session
):
    """Verify email sending rejects when confirm_send=False or recipient is invalid."""
    from app.services.gmail_service import GmailService

    user = _create_user(db_session, "gmail_safety_user")

    # 1. Missing explicit confirmation must raise ForbiddenError
    with pytest.raises(Exception) as excinfo:
        GmailService.send_email(
            db=db_session,
            user=user,
            recipient_email="recruiter@company.com",
            subject="Job Inquiry",
            body="Hello hiring team",
            confirm_send=False,  # Forbidden!
        )
    assert "Explicit user confirmation is strictly required" in str(excinfo.value)

    # 2. Missing/guessed recipient email must raise BadRequestError
    with pytest.raises(Exception) as excinfo2:
        GmailService.send_email(
            db=db_session,
            user=user,
            recipient_email="not-an-email",
            subject="Job Inquiry",
            body="Hello hiring team",
            confirm_send=True,
        )
    assert "valid explicit recipient email address" in str(excinfo2.value)
