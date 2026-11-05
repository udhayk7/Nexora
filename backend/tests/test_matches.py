import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.analysis import ResumeAnalysis
from app.models.company import Company
from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import ResumeAnalysisResult
from app.services.matching_engine import MatchingEngine


def get_mock_analysis_dict() -> dict[str, Any]:
    return {
        "profile": {
            "summary": "Junior Software Engineer proficient in Python, FastAPI, and PostgreSQL.",
            "domains": ["Backend Development", "Web Services"],
            "career_level_estimate": "Junior (1-2 years evidenced)",
            "evidence": [
                {"section": "Summary", "excerpt": "Junior engineer with 1 year Python experience"},
            ],
        },
        "skills": {
            "categorized_skills": {
                "Languages": ["Python", "JavaScript"],
                "Backend": ["FastAPI", "PostgreSQL"],
                "Tools": ["Docker", "Git"],
            },
            "supported_skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
            "unevidenced_skills": ["Docker", "JavaScript"],
            "evidence": [
                {"section": "Skills", "excerpt": "Python, FastAPI, PostgreSQL, Git, Docker"},
                {
                    "section": "Projects",
                    "excerpt": "Built REST API service using FastAPI and PostgreSQL",
                },
            ],
        },
        "experience_evidence": {
            "summary": "Demonstrated experience building backend microservices.",
            "measurable_outcomes": ["Reduced API latency by 20%"],
            "vague_or_unsupported_claims": [],
            "evidence": [
                {
                    "section": "Experience",
                    "excerpt": "Junior Backend Developer at TechCorp - 2023 to Present",
                },
            ],
        },
        "strengths": [
            {
                "strength": "Grounded API development experience with modern Python tools",
                "evidence": {
                    "section": "Projects",
                    "excerpt": "FastAPI service with PostgreSQL database",
                },
            }
        ],
        "improvement_opportunities": [],
        "role_suitability": [
            {
                "role_name": "Software Engineer",
                "suitability_band": "Strong Match",
                "heuristic_score": 90,
                "confidence": "High",
                "strengths": ["Strong foundational backend engineering skills in Python"],
                "gaps": [],
                "evidence": [
                    {"section": "Skills", "excerpt": "Python, FastAPI, PostgreSQL"},
                ],
                "disclaimer": "Heuristic AI assessment based on resume evidence.",
            },
            {
                "role_name": "Backend Developer",
                "suitability_band": "Strong Match",
                "heuristic_score": 95,
                "confidence": "High",
                "strengths": ["Direct hands-on experience with FastAPI and PostgreSQL"],
                "gaps": [],
                "evidence": [
                    {"section": "Skills", "excerpt": "FastAPI, PostgreSQL"},
                ],
                "disclaimer": "Heuristic AI assessment based on resume evidence.",
            },
        ],
        "recommendations": [],
    }


def create_test_user_and_auth(
    client: TestClient,
    email: str = "matcher@example.com",
) -> tuple[dict[str, str], str]:
    reg_payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Alex Matcher",
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, email


def test_matching_engine_deterministic_scoring() -> None:
    """Test deterministic scoring algorithm directly."""
    analysis_data = get_mock_analysis_dict()
    analysis = ResumeAnalysisResult.model_validate(analysis_data)

    job = Job(
        id=uuid.uuid4(),
        title="Junior Backend Engineer",
        role_family="Software Engineer",
        seniority_level="entry_level",
        work_arrangement="remote",
        city="San Francisco",
        country="USA",
        description="Looking for an entry-level Python and FastAPI engineer with PostgreSQL.",
        skills_tags=["Python", "FastAPI", "PostgreSQL", "Docker"],
        salary_min=80000,
        salary_max=100000,
        salary_currency="USD",
        salary_period="year",
        verification_status="verified",
        job_status="active",
    )

    prefs = UserMatchingPreference(
        target_role_families=["Software Engineer", "Backend Developer"],
        preferred_locations=["San Francisco", "Remote"],
        work_arrangement_preferences=["remote"],
        min_salary=75000,
        preferred_skills=["Python", "FastAPI"],
    )

    match_score, breakdown, positives, gaps = MatchingEngine.evaluate_match(
        job=job,
        resume_analysis=analysis,
        preferences=prefs,
    )

    assert match_score >= 80.0
    assert breakdown.skills_score >= 80.0
    assert breakdown.role_score >= 80.0
    assert breakdown.experience_score >= 85.0
    assert breakdown.location_score >= 80.0
    assert breakdown.salary_status in {"matched", "above_minimum"}
    assert breakdown.trust_adjustment > 0  # verified + recent bonus
    assert len(positives) > 0
    assert any(p.dimension == "skills" for p in positives)


def test_undisclosed_salary_never_penalized() -> None:
    """Test that a listing without salary does not penalize score and reallocates weights."""
    analysis_data = get_mock_analysis_dict()
    analysis = ResumeAnalysisResult.model_validate(analysis_data)

    # Job without salary
    job_no_sal = Job(
        id=uuid.uuid4(),
        title="Junior Backend Developer",
        role_family="Software Engineer",
        seniority_level="entry_level",
        work_arrangement="remote",
        description="Python backend developer wanted.",
        skills_tags=["Python", "FastAPI"],
        salary_min=None,
        salary_max=None,
        verification_status="verified",
        job_status="active",
    )

    # Job with matching salary
    job_with_sal = Job(
        id=uuid.uuid4(),
        title="Junior Backend Developer",
        role_family="Software Engineer",
        seniority_level="entry_level",
        work_arrangement="remote",
        description="Python backend developer wanted.",
        skills_tags=["Python", "FastAPI"],
        salary_min=85000,
        salary_max=100000,
        salary_period="year",
        verification_status="verified",
        job_status="active",
    )

    prefs = UserMatchingPreference(
        target_role_families=["Software Engineer"],
        work_arrangement_preferences=["remote"],
        min_salary=80000,
        preferred_skills=["Python"],
    )

    score_no_sal, bd_no_sal, _, _ = MatchingEngine.evaluate_match(
        job=job_no_sal, resume_analysis=analysis, preferences=prefs
    )
    score_with_sal, bd_with_sal, _, _ = MatchingEngine.evaluate_match(
        job=job_with_sal, resume_analysis=analysis, preferences=prefs
    )

    # Undisclosed salary must have None score and 'undisclosed' status
    assert bd_no_sal.salary_score is None
    assert bd_no_sal.salary_status == "undisclosed"
    assert sum(bd_no_sal.weights_applied.values()) == pytest.approx(1.0, 0.001)

    # Undisclosed salary should NOT depress score (within minor rounding differences)
    assert score_no_sal >= 85.0
    assert abs(score_no_sal - score_with_sal) < 5.0


def test_missing_info_vs_true_mismatch_signals() -> None:
    """Test that missing listing info is classified as 'missing', whereas conflict is 'mismatch'."""
    analysis_data = get_mock_analysis_dict()
    analysis = ResumeAnalysisResult.model_validate(analysis_data)

    # Job with missing seniority
    job_missing = Job(
        id=uuid.uuid4(),
        title="Backend Developer",
        role_family="Software Engineer",
        seniority_level=None,
        work_arrangement="unspecified",
        skills_tags=[],
        job_status="active",
    )

    # Job with conflicting seniority (Staff level for Junior candidate)
    job_mismatch = Job(
        id=uuid.uuid4(),
        title="Staff Backend Architect",
        role_family="Engineering Leadership",
        seniority_level="staff",
        work_arrangement="onsite",
        skills_tags=["C++", "Rust"],
        job_status="active",
    )

    prefs = UserMatchingPreference(
        target_role_families=["Software Engineer"],
        work_arrangement_preferences=["remote"],
    )

    _, _, _, gaps_missing = MatchingEngine.evaluate_match(
        job=job_missing, resume_analysis=analysis, preferences=prefs
    )
    assert any(g.type == "missing" for g in gaps_missing)

    _, _, _, gaps_mismatch = MatchingEngine.evaluate_match(
        job=job_mismatch, resume_analysis=analysis, preferences=prefs
    )
    assert any(g.type == "mismatch" for g in gaps_mismatch)


def test_preferences_api_defaults_and_updates(client: TestClient) -> None:
    """Test retrieving and updating user matching preferences."""
    headers, _ = create_test_user_and_auth(client, email="pref_user@example.com")

    # 1. GET default preferences
    get_resp = client.get("/api/v1/matches/preferences", headers=headers)
    assert get_resp.status_code == 200
    pref_data = get_resp.json()
    assert pref_data["target_role_families"] == []
    assert pref_data["preferred_skills"] == []

    # 2. PUT update preferences
    update_payload = {
        "target_role_families": ["Backend Developer", "Full Stack Engineer"],
        "preferred_locations": ["San Francisco, CA", "New York, NY"],
        "preferred_work_arrangements": ["remote", "hybrid"],
        "min_salary": 90000,
        "salary_period": "year",
        "preferred_skills": ["Python", "FastAPI", "PostgreSQL"],
        "excluded_roles": ["Sales Engineer"],
        "excluded_terms": ["Crypto", "Web3"],
        "excluded_industries": ["Gambling"],
    }
    put_resp = client.put("/api/v1/matches/preferences", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["min_salary"] == 90000
    assert "Backend Developer" in updated_data["target_role_families"]
    assert "Gambling" in updated_data["excluded_industries"]

    # 3. GET persists correctly
    verify_resp = client.get("/api/v1/matches/preferences", headers=headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["min_salary"] == 90000


def test_match_run_listing_and_detail(client: TestClient, db_session: Session) -> None:
    """End-to-end integration test of match calculation, listing, details, and idempotency."""
    headers, user_email = create_test_user_and_auth(client, email="e2e_matcher@example.com")
    user = db_session.query(User).filter(User.email == user_email).first()
    assert user is not None

    # Create Resume & Version
    resume = Resume(id=uuid.uuid4(), user_id=user.id, title="Backend Resume")
    db_session.add(resume)
    db_session.commit()

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="resume.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/test_res.pdf",
        parsing_status="completed",
        raw_text="Python FastAPI Developer",
    )
    db_session.add(version)
    resume.current_version_id = version.id
    db_session.commit()

    # Create Analysis
    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=version.id,
        status="completed",
        provider="gemini",
        model="gemini-2.5-flash",
        result=get_mock_analysis_dict(),
    )
    db_session.add(analysis)

    # Create 2 Jobs
    company = Company(
        id=uuid.uuid4(),
        name="Nexora Tech",
        normalized_name="nexora tech",
        category="product_company",
        website_url="https://nexoratech.example.com",
    )
    db_session.add(company)
    db_session.commit()

    job1 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Junior Python Engineer",
        normalized_title="junior python engineer",
        job_url="https://nexoratech.example.com/jobs/1",
        role_family="Software Engineer",
        seniority_level="entry_level",
        work_arrangement="remote",
        description="Join our team building FastAPI backends with PostgreSQL.",
        skills_tags=["Python", "FastAPI", "PostgreSQL"],
        salary_min=85000,
        salary_max=95000,
        salary_period="year",
        verification_status="verified",
        job_status="active",
        canonical_url_hash="hash_test_job_1",
    )
    job2 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Closed Legacy Job",
        normalized_title="closed legacy job",
        job_url="https://nexoratech.example.com/jobs/2",
        description="Closed legacy requisition",
        role_family="Other",
        job_status="closed",  # closed job should be skipped by matching run
        canonical_url_hash="hash_test_job_2",
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    # 1. Trigger Match Run
    run_resp = client.post(
        "/api/v1/matches/run",
        json={
            "resume_id": str(resume.id),
            "version_id": str(version.id),
            "min_score_threshold": 50.0,
        },
        headers=headers,
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["matches_computed"] >= 1
    assert run_data["matches_saved"] >= 1

    # 2. List Matches
    list_resp = client.get("/api/v1/matches", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    match_item = list_data["items"][0]
    match_id = match_item["id"]
    assert match_item["match_score"] >= 70.0
    assert match_item["job"]["title"] == "Junior Python Engineer"

    # 3. Get Match Detail
    detail_resp = client.get(f"/api/v1/matches/{match_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["score_breakdown"]["skills_score"] >= 70.0
    assert len(detail_data["positive_signals"]) > 0

    # 4. Save and Dismiss Toggles
    save_resp = client.patch(
        f"/api/v1/matches/{match_id}",
        json={"is_saved": True},
        headers=headers,
    )
    assert save_resp.status_code == 200
    assert save_resp.json()["is_saved"] is True

    # Filter saved matches
    saved_list_resp = client.get("/api/v1/matches?is_saved=true", headers=headers)
    assert saved_list_resp.status_code == 200
    assert len(saved_list_resp.json()["items"]) >= 1

    dismiss_resp = client.patch(
        f"/api/v1/matches/{match_id}",
        json={"is_dismissed": True},
        headers=headers,
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["is_dismissed"] is True

    # Default list excludes dismissed matches
    active_list_resp = client.get("/api/v1/matches", headers=headers)
    assert active_list_resp.status_code == 200
    assert len(active_list_resp.json()["items"]) == 0

    # 5. Idempotency check: re-running does not create duplicate rows
    run_resp_2 = client.post(
        "/api/v1/matches/run",
        json={"resume_id": str(resume.id), "version_id": str(version.id)},
        headers=headers,
    )
    assert run_resp_2.status_code == 200
    list_resp_2 = client.get("/api/v1/matches?include_dismissed=true", headers=headers)
    assert list_resp_2.status_code == 200
    assert list_resp_2.json()["total"] == 1  # Still 1 record, updated in place


def test_multi_tenant_match_isolation(client: TestClient, db_session: Session) -> None:
    """Ensure User A cannot view or modify User B's preferences or match results."""
    headers_a, _ = create_test_user_and_auth(client, email="usera@example.com")
    headers_b, _ = create_test_user_and_auth(client, email="userb@example.com")

    # User A updates preferences
    client.put(
        "/api/v1/matches/preferences",
        json={"target_role_families": ["Backend Developer"]},
        headers=headers_a,
    )

    # User B should have separate empty preferences
    b_pref_resp = client.get("/api/v1/matches/preferences", headers=headers_b)
    assert b_pref_resp.status_code == 200
    assert b_pref_resp.json()["target_role_families"] == []

    # Nonexistent match for user returns 404
    fake_match_id = str(uuid.uuid4())
    get_404 = client.get(f"/api/v1/matches/{fake_match_id}", headers=headers_b)
    assert get_404.status_code == 404

    patch_404 = client.patch(
        f"/api/v1/matches/{fake_match_id}",
        json={"is_saved": True},
        headers=headers_b,
    )
    assert patch_404.status_code == 404
