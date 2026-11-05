from typing import Any
from unittest.mock import MagicMock

import docx
import pytest
from fastapi.testclient import TestClient

from app.core.audit import audit_service
from app.core.config import settings
from app.schemas.analysis import ResumeAnalysisResult
from app.services.ai.base import (
    AIConfigurationError,
    AIProviderError,
    AIProviderResponse,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.factory import get_ai_provider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_mock_valid_analysis_dict() -> dict[str, Any]:
    return {
        "profile": {
            "summary": "Experienced Full Stack Engineer with expertise in Python systems.",
            "domains": ["Distributed Systems", "Backend API Development", "Cloud Architecture"],
            "career_level_estimate": "Senior (6+ years evidenced)",
            "evidence": [
                {"section": "Summary", "excerpt": "Full-stack engineer with 6 years experience"},
            ],
        },
        "skills": {
            "categorized_skills": {
                "Languages": ["Python", "TypeScript"],
                "Backend": ["FastAPI", "PostgreSQL"],
                "DevOps": ["Docker", "Kubernetes"],
            },
            "supported_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
            "unevidenced_skills": ["Kubernetes"],
            "evidence": [
                {"section": "Skills", "excerpt": "Python, FastAPI, TypeScript, React, Docker"},
                {"section": "Experience", "excerpt": "Architected low-latency distributed APIs"},
            ],
        },
        "experience_evidence": {
            "summary": "Demonstrated history of backend architecture and microservice migrations.",
            "measurable_outcomes": ["Led migration from monolith to microservices"],
            "vague_or_unsupported_claims": ["Improved API performance without specific metrics"],
            "evidence": [
                {
                    "section": "Experience",
                    "excerpt": "Senior Engineer at NexaCorp - Jan 2021 to Present",
                },
            ],
        },
        "strengths": [
            {
                "strength": (
                    "Strong backend architectural track record with concrete framework experience"
                ),
                "evidence": {
                    "section": "Experience",
                    "excerpt": "Architected low-latency distributed APIs",
                },
            }
        ],
        "improvement_opportunities": [
            {
                "category": "vague_bullet",
                "issue": "Lack of quantifiable business metrics on microservice migration",
                "suggestion": "Quantify latency decrease or throughput improvement achieved",
                "referenced_excerpt": "Led migration from monolith to microservices",
            }
        ],
        "role_suitability": [
            {
                "role_name": "Python Backend Developer",
                "suitability_band": "Strong Match",
                "heuristic_score": 92,
                "confidence": "High",
                "strengths": [
                    "Deep FastAPI and PostgreSQL experience",
                    "Distributed systems design",
                ],
                "gaps": ["Lacks cloud infrastructure automation metrics"],
                "evidence": [
                    {"section": "Experience", "excerpt": "Architected low-latency APIs"},
                ],
                "disclaimer": (
                    "Heuristic AI assessment based on resume evidence, not a hiring guarantee."
                ),
            },
            {
                "role_name": "Full Stack Developer",
                "suitability_band": "Good Match",
                "heuristic_score": 80,
                "confidence": "Medium",
                "strengths": ["React and TypeScript mentioned"],
                "gaps": ["Fewer frontend project bullet points than backend"],
                "evidence": [
                    {"section": "Skills", "excerpt": "TypeScript, React"},
                ],
                "disclaimer": (
                    "Heuristic AI assessment based on resume evidence, not a hiring guarantee."
                ),
            },
        ],
        "recommendations": [
            {
                "priority": "high",
                "title": "Quantify Backend Performance Impact",
                "issue": "Impact of microservice migration is described qualitatively",
                "why_it_matters": "Quantified outcomes provide credible proof of impact",
                "suggested_action": "Add percentages or latency metrics (e.g., p99 latency cut)",
                "referenced_evidence": "Led migration from monolith to microservices",
            }
        ],
    }


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


@pytest.fixture
def auth_headers_user1(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ai_user1@example.com",
            "password": "Password123!",
            "full_name": "AI User 1",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ai_user2@example.com",
            "password": "Password123!",
            "full_name": "AI User 2",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def uploaded_resume(client: TestClient, auth_headers_user1: dict[str, str]) -> dict[str, Any]:
    # Upload a valid docx resume
    doc = docx.Document()
    doc.add_heading("Jane Dev", level=1)
    doc.add_paragraph("jane.dev@example.com | 555-432-1098")
    doc.add_heading("Technical Skills", level=2)
    doc.add_paragraph("Python, FastAPI, TypeScript, React, Docker, PostgreSQL")
    doc.add_heading("Work Experience", level=2)
    doc.add_paragraph("Senior Engineer at NexaCorp - Jan 2021 to Present")
    doc.add_paragraph("• Architected low-latency distributed APIs")
    doc.add_paragraph("• Led migration from monolith to microservices")

    import io

    buf = io.BytesIO()
    doc.save(buf)
    content = buf.getvalue()

    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    files = {"file": ("jane_resume.docx", content, mime)}
    res = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)
    assert res.status_code == 201
    return res.json()


# 1. Provider Configuration & Missing Key Tests
def test_gemini_missing_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    provider = GeminiProvider(api_key="")
    assert not provider.is_configured
    with pytest.raises(AIConfigurationError) as exc_info:
        provider.analyze_resume("Resume content")
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_openai_missing_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    provider = OpenAIProvider(api_key="")
    assert not provider.is_configured
    with pytest.raises(AIConfigurationError) as exc_info:
        provider.analyze_resume("Resume content")
    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_disabled_provider_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "none")
    with pytest.raises(AIConfigurationError) as exc_info:
        get_ai_provider()
    assert "AI features are disabled" in str(exc_info.value)


def test_unknown_provider_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    with pytest.raises(AIConfigurationError) as exc_info:
        get_ai_provider()
    assert "Unsupported AI provider" in str(exc_info.value)


# 2. Structured Output & Mocked Provider Tests
def test_gemini_provider_mocked_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(api_key="mock_key_test")
    valid_data = get_mock_valid_analysis_dict()

    import json

    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_data)
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 1200
    mock_usage.candidates_token_count = 800
    mock_usage.total_token_count = 2000
    mock_response.usage_metadata = mock_usage

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    result = provider.analyze_resume("Jane Dev resume text")
    assert result.provider == "gemini"
    assert result.result.profile.career_level_estimate == "Senior (6+ years evidenced)"
    assert result.prompt_tokens == 1200
    assert result.completion_tokens == 800
    assert result.total_tokens == 2000
    assert result.estimated_cost_usd is not None


def test_openai_provider_mocked_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIProvider(api_key="mock_openai_key")
    valid_data = get_mock_valid_analysis_dict()

    validated = ResumeAnalysisResult.model_validate(valid_data)

    mock_parsed_msg = MagicMock()
    mock_parsed_msg.refusal = None
    mock_parsed_msg.parsed = validated

    mock_choice = MagicMock()
    mock_choice.message = mock_parsed_msg

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 1000
    mock_usage.completion_tokens = 500
    mock_usage.total_tokens = 1500

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_completion
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    result = provider.analyze_resume("Jane Dev resume text")
    assert result.provider == "openai"
    assert result.result.profile.career_level_estimate == "Senior (6+ years evidenced)"
    assert result.total_tokens == 1500


def test_provider_malformed_json_raises_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(api_key="mock_key")
    mock_response = MagicMock()
    mock_response.text = "NOT_A_VALID_JSON"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(AIProviderError):
        provider.analyze_resume("Resume content")


def test_provider_timeout_raises_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(api_key="mock_key")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Read timed out after 30s")
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(AITimeoutError):
        provider.analyze_resume("Resume content")


def test_provider_rate_limit_raises_rate_limit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GeminiProvider(api_key="mock_key")
    mock_client = MagicMock()
    err_msg = "429 ResourceExhausted: Quota exceeded"
    mock_client.models.generate_content.side_effect = Exception(err_msg)
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(AIRateLimitError):
        provider.analyze_resume("Resume content")


# 3. API Endpoints & User Scoping
def test_api_analyze_resume_success(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    uploaded_resume: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = uploaded_resume["id"]
    version_id = uploaded_resume["current_version"]["id"]

    valid_dict = get_mock_valid_analysis_dict()
    valid_res = ResumeAnalysisResult.model_validate(valid_dict)

    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model_name = "gemini-2.5-flash"
    mock_provider.analyze_resume.return_value = AIProviderResponse(
        result=valid_res,
        provider="gemini",
        model="gemini-2.5-flash",
        prompt_tokens=1500,
        completion_tokens=600,
        total_tokens=2100,
        estimated_cost_usd=0.0003,
    )
    monkeypatch.setattr("app.services.ai.analyzer.get_ai_provider", lambda _: mock_provider)

    res = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
        json={"force_refresh": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["provider"] == "gemini"
    assert body["result"]["profile"]["career_level_estimate"] == "Senior (6+ years evidenced)"
    assert len(body["result"]["role_suitability"]) == 2
    assert body["total_tokens"] == 2100


def test_api_deduplication_cache_behavior(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    uploaded_resume: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = uploaded_resume["id"]
    version_id = uploaded_resume["current_version"]["id"]

    valid_res = ResumeAnalysisResult.model_validate(get_mock_valid_analysis_dict())
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model_name = "gemini-2.5-flash"
    mock_provider.analyze_resume.return_value = AIProviderResponse(
        result=valid_res,
        provider="gemini",
        model="gemini-2.5-flash",
        total_tokens=1000,
    )
    monkeypatch.setattr("app.services.ai.analyzer.get_ai_provider", lambda _: mock_provider)

    # First call: triggers analysis
    res1 = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
        json={"force_refresh": False},
    )
    assert res1.status_code == 200
    analysis1_id = res1.json()["id"]
    assert mock_provider.analyze_resume.call_count == 1

    # Second call without force_refresh: returns cached record without re-calling provider
    res2 = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
        json={"force_refresh": False},
    )
    assert res2.status_code == 200
    assert res2.json()["id"] == analysis1_id
    assert mock_provider.analyze_resume.call_count == 1  # Unchanged!

    # Third call WITH force_refresh=True: calls provider again
    res3 = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
        json={"force_refresh": True},
    )
    assert res3.status_code == 200
    assert mock_provider.analyze_resume.call_count == 2


def test_user_isolation_cannot_access_other_user_analysis(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
    uploaded_resume: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = uploaded_resume["id"]
    version_id = uploaded_resume["current_version"]["id"]

    valid_res = ResumeAnalysisResult.model_validate(get_mock_valid_analysis_dict())
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model_name = "gemini-2.5-flash"
    mock_provider.analyze_resume.return_value = AIProviderResponse(
        result=valid_res, provider="gemini", model="gemini-2.5-flash"
    )
    monkeypatch.setattr("app.services.ai.analyzer.get_ai_provider", lambda _: mock_provider)

    # User 1 performs analysis
    res_analyze = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
    )
    analysis_id = res_analyze.json()["id"]

    # User 2 attempts to trigger analysis on User 1's resume -> 404
    res_u2_post = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user2,
    )
    assert res_u2_post.status_code == 404

    # User 2 attempts to list analyses for User 1's resume -> 404
    res_u2_list = client.get(
        f"/api/v1/resumes/{resume_id}/analysis",
        headers=auth_headers_user2,
    )
    assert res_u2_list.status_code == 404

    # User 2 attempts to get specific analysis -> 404
    res_u2_get = client.get(
        f"/api/v1/resumes/{resume_id}/analysis/{analysis_id}",
        headers=auth_headers_user2,
    )
    assert res_u2_get.status_code == 404


def test_list_and_get_analysis_history(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    uploaded_resume: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = uploaded_resume["id"]
    version_id = uploaded_resume["current_version"]["id"]

    valid_res = ResumeAnalysisResult.model_validate(get_mock_valid_analysis_dict())
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model_name = "gemini-2.5-flash"
    mock_provider.analyze_resume.return_value = AIProviderResponse(
        result=valid_res, provider="gemini", model="gemini-2.5-flash"
    )
    monkeypatch.setattr("app.services.ai.analyzer.get_ai_provider", lambda _: mock_provider)

    # Trigger analysis
    res_created = client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
    )
    analysis_id = res_created.json()["id"]

    # List analyses
    res_list = client.get(f"/api/v1/resumes/{resume_id}/analysis", headers=auth_headers_user1)
    assert res_list.status_code == 200
    analyses = res_list.json()
    assert len(analyses) >= 1
    assert analyses[0]["id"] == analysis_id
    assert analyses[0]["career_level"] == "Senior (6+ years evidenced)"

    # Get status
    res_status = client.get(
        f"/api/v1/resumes/{resume_id}/analysis/{analysis_id}/status",
        headers=auth_headers_user1,
    )
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "completed"


def test_audit_events_and_privacy_on_analysis(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    uploaded_resume: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    resume_id = uploaded_resume["id"]
    version_id = uploaded_resume["current_version"]["id"]

    valid_res = ResumeAnalysisResult.model_validate(get_mock_valid_analysis_dict())
    mock_provider = MagicMock()
    mock_provider.name = "gemini"
    mock_provider.model_name = "gemini-2.5-flash"
    mock_provider.analyze_resume.return_value = AIProviderResponse(
        result=valid_res, provider="gemini", model="gemini-2.5-flash", total_tokens=1500
    )
    monkeypatch.setattr("app.services.ai.analyzer.get_ai_provider", lambda _: mock_provider)

    client.post(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/analysis",
        headers=auth_headers_user1,
    )

    actions = [e.action for e in sink.events]
    assert "resume.analysis_requested" in actions
    assert "resume.analysis_completed" in actions

    # Verify PRIVACY: audit metadata does NOT contain resume text or sensitive candidate contact
    for e in sink.events:
        metadata_str = str(e.metadata)
        assert "jane.dev@example.com" not in metadata_str
        assert "555-432-1098" not in metadata_str
        assert "api_key" not in metadata_str
