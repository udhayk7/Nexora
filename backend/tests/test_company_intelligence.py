"""Unit and integration tests for Company Intelligence & Research module."""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.services.company_intelligence.adapters import (
    ResearchSourcePayload,
    SimpleHTMLTextExtractor,
)
from app.services.company_intelligence.fit_evaluator import evaluate_company_fit
from app.services.company_intelligence.technology_extractor import (
    extract_technologies_with_evidence,
)
from app.services.company_intelligence_service import CompanyIntelligenceService


@pytest.fixture(autouse=True)
def mock_web_adapter():
    payload1 = ResearchSourcePayload(
        source_type="official_website",
        source_url="https://stripe.com",
        title="Stripe - Financial Infrastructure",
        content_snippet="Global economic infrastructure provider using Python and PostgreSQL.",
        raw_content="Stripe develops financial infrastructure using Python, Go, and PostgreSQL.",
        content_hash="mockhash123",
        retrieved_at=datetime.utcnow(),
        is_verified=True,
    )
    with patch(
        "app.services.company_intelligence.adapters.OfficialWebsiteAdapter.fetch_company_sources",
        return_value=[payload1],
    ):
        yield


def create_user_and_auth(
    client: TestClient, email: str = "researcher@example.com"
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Company Researcher",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_test_entities(db: Session, email: str) -> tuple[User, Company, list[Job]]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Company Researcher",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="Stripe Technologies",
        normalized_name="stripe technologies",
        website_url="https://stripe.com",
        careers_url="https://stripe.com/jobs",
        category="product_company",
        headquarters_city="San Francisco",
        headquarters_country="United States",
        industry_tags=["Fintech", "Payments"],
        technology_tags=["Python", "Go", "AWS", "PostgreSQL"],
        description="Global economic infrastructure provider supporting online payments.",
    )
    db.add(company)
    db.flush()

    # Create 3 jobs for company: 1 entry level active, 1 internship active, 1 expired
    job1 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Junior Software Engineer - Backend",
        normalized_title="junior software engineer backend",
        description="Build payment rails using Python, FastAPI, and PostgreSQL with AWS.",
        seniority_level="entry_level",
        work_arrangement="remote",
        location_text="Remote, US",
        role_family="Backend Engineering",
        job_url="https://stripe.com/jobs/1",
        job_status="active",
        skills_tags=["Python", "FastAPI", "PostgreSQL", "AWS"],
    )
    job2 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Software Engineering Intern",
        normalized_title="software engineering intern",
        description="Summer internship working on distributed event systems with Go and Kafka.",
        seniority_level="internship",
        work_arrangement="hybrid",
        location_text="San Francisco, CA",
        role_family="Backend Engineering",
        job_url="https://stripe.com/jobs/2",
        job_status="active",
        skills_tags=["Go", "Kafka", "Docker"],
    )
    job3 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Senior Security Architect",
        normalized_title="senior security architect",
        description="Archived position for security lead.",
        seniority_level="senior",
        work_arrangement="onsite",
        job_url="https://stripe.com/jobs/3",
        job_status="expired",
        skills_tags=["Rust", "Cryptography"],
    )
    db.add_all([job1, job2, job3])
    db.commit()

    return user, company, [job1, job2, job3]


# ============================================================================
# Unit Tests
# ============================================================================


def test_simple_html_text_extractor():
    html = """
    <html>
        <head><title>Stripe | Financial Infrastructure</title></head>
        <body>
            <style>.hide { display: none; }</style>
            <script>console.log('secret');</script>
            <h1>Financial Infrastructure for the Internet</h1>
            <p>Millions of companies use Stripe to accept payments and manage businesses online.</p>
        </body>
    </html>
    """
    parser = SimpleHTMLTextExtractor()
    parser.feed(html)
    assert "Financial Infrastructure" in parser.title
    text = parser.get_clean_text()
    assert "Millions of companies use Stripe" in text
    assert "console.log" not in text
    assert ".hide" not in text


def test_technology_extraction_with_evidence():
    official_text = "We build our core platform using Python and PostgreSQL running in AWS."
    job_descriptions = [
        "We are looking for Python developers with Docker and FastAPI experience.",
        "Backend role requiring Python, FastAPI, and Redis expertise.",
    ]
    tags = ["Go"]

    techs = extract_technologies_with_evidence(
        official_sources_text=official_text,
        job_descriptions=job_descriptions,
        company_tags=tags,
    )

    names = {t["name"]: t for t in techs}
    # Python is in official text -> confirmed
    assert "Python" in names
    assert names["Python"]["evidence_strength"] == "confirmed"

    # PostgreSQL is in official text -> confirmed
    assert "PostgreSQL" in names
    assert names["PostgreSQL"]["evidence_strength"] == "confirmed"

    # FastAPI is in 2 jobs -> supported
    assert "FastAPI" in names
    assert names["FastAPI"]["evidence_strength"] == "supported"

    # Go is from company tags -> inferred
    assert "Go" in names
    assert names["Go"]["evidence_strength"] == "inferred"


def test_candidate_fit_evaluation():
    company_id = uuid.uuid4()
    company_technologies = [
        {"name": "Python", "evidence_strength": "confirmed"},
        {"name": "PostgreSQL", "evidence_strength": "confirmed"},
        {"name": "FastAPI", "evidence_strength": "supported"},
        {"name": "Kubernetes", "evidence_strength": "supported"},
    ]
    candidate_skills = ["Python", "FastAPI", "Docker"]
    candidate_target_roles = ["Backend Engineering"]
    company_jobs = [
        {
            "id": str(uuid.uuid4()),
            "title": "Junior Backend Engineer",
            "role_family": "Backend Engineering",
            "seniority_level": "entry_level",
            "location_text": "Remote",
            "job_status": "active",
        }
    ]

    fit = evaluate_company_fit(
        company_id=company_id,
        company_name="Test Corp",
        company_technologies=company_technologies,
        candidate_skills=candidate_skills,
        candidate_target_roles=candidate_target_roles,
        company_jobs=company_jobs,
    )

    assert fit["fit_score"] > 50
    assert fit["fit_level"] in ("strong", "moderate")
    assert any("Python" in s for s in fit["matching_skills"])
    assert any("FastAPI" in s for s in fit["matching_skills"])
    assert any("Kubernetes" in g for g in fit["missing_or_gap_skills"])
    assert len(fit["target_role_matches"]) == 1
    assert len(fit["recommended_interview_focus"]) > 0


# ============================================================================
# Service Layer Tests
# ============================================================================


def test_compute_hiring_summary_from_db_jobs(db_session: Session):
    _, company, _ = setup_test_entities(db_session, "hire_test@example.com")
    service = CompanyIntelligenceService(db_session)
    summary, active_jobs = service.compute_hiring_summary(company.id)

    assert summary["total_active_jobs"] == 2
    assert summary["entry_level_jobs"] == 2  # junior + intern
    assert summary["internship_jobs"] == 1
    assert summary["stale_or_expired_jobs"] == 1
    assert len(active_jobs) == 2
    assert (
        "San Francisco, CA" in summary["top_locations"] or "Remote, US" in summary["top_locations"]
    )


def test_generate_and_cache_research_report(db_session: Session):
    user, company, _ = setup_test_entities(db_session, "cache_test@example.com")
    service = CompanyIntelligenceService(db_session)

    from app.schemas.company_intelligence import CompanyResearchGenerateRequest

    req = CompanyResearchGenerateRequest(force_refresh=False)
    report1 = service.generate_research_report(user=user, company_id=company.id, req=req)

    assert report1 is not None
    assert report1.company_id == company.id
    assert report1.user_id == user.id
    assert report1.is_cached is False
    assert len(report1.sections) == 10

    # Ensure all 10 required sections are present
    required_keys = [
        "overview",
        "products_and_services",
        "technology_landscape",
        "engineering_culture",
        "hiring_activity",
        "entry_level_opportunities",
        "candidate_alignment",
        "interview_prep_topics",
        "recruiter_interviewer_questions",
        "sources_and_evidence",
    ]
    for k in required_keys:
        assert k in report1.sections
        assert "title" in report1.sections[k]
        assert "content" in report1.sections[k]
        assert "bullet_points" in report1.sections[k]

    # Generate again without force_refresh: should hit cache!
    report2 = service.generate_research_report(user=user, company_id=company.id, req=req)
    assert report2.id == report1.id
    assert report2.is_cached is True


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================


def test_get_company_intelligence_endpoint(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "intel_api@example.com")
    _, company, _ = setup_test_entities(db_session, email)

    res = client.get(f"/api/v1/companies/{company.id}/intelligence", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["company_id"] == str(company.id)
    assert data["company_name"] == company.name
    assert "hiring_summary" in data
    assert data["hiring_summary"]["total_active_jobs"] == 2
    assert "technology_stack" in data


def test_get_company_technology_endpoint(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "tech_api@example.com")
    _, company, _ = setup_test_entities(db_session, email)

    res = client.get(f"/api/v1/companies/{company.id}/technology", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check technology items have valid evidence strength
    for item in data:
        assert item["evidence_strength"] in ("confirmed", "supported", "inferred", "unknown")
        assert "evidence_source" in item


def test_get_company_hiring_endpoint(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "hiring_api@example.com")
    _, company, _ = setup_test_entities(db_session, email)

    res = client.get(f"/api/v1/companies/{company.id}/hiring", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_active_jobs"] == 2
    assert data["internship_jobs"] == 1
    assert data["stale_or_expired_jobs"] == 1


def test_get_company_fit_endpoint(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "fit_api@example.com")
    _, company, _ = setup_test_entities(db_session, email)

    res = client.get(f"/api/v1/companies/{company.id}/fit", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["company_id"] == str(company.id)
    assert 0 <= data["fit_score"] <= 100
    assert data["fit_level"] in ("strong", "moderate", "developing")
    assert isinstance(data["matching_skills"], list)
    assert isinstance(data["recommended_interview_focus"], list)


def test_generate_and_list_research_reports_api(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "report_api@example.com")
    _, company, _ = setup_test_entities(db_session, email)

    # 1. Generate Report
    post_res = client.post(
        f"/api/v1/companies/{company.id}/research/generate",
        json={"force_refresh": False, "focus_areas": ["tech_stack", "entry_level"]},
        headers=headers,
    )
    assert post_res.status_code == 201
    report_data = post_res.json()
    report_id = report_data["id"]
    assert report_data["report_title"].startswith("Company Intelligence & Fit Report")
    assert len(report_data["sections"]) == 10

    # 2. List company reports for this company
    list_c_res = client.get(f"/api/v1/companies/{company.id}/research/reports", headers=headers)
    assert list_c_res.status_code == 200
    assert len(list_c_res.json()) >= 1

    # 3. List all user reports
    list_all_res = client.get("/api/v1/company-intelligence/reports", headers=headers)
    assert list_all_res.status_code == 200
    assert len(list_all_res.json()) >= 1

    # 4. Get specific report detail
    detail_res = client.get(f"/api/v1/company-intelligence/reports/{report_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == report_id


def test_company_intelligence_404_for_unknown_company(client: TestClient, db_session: Session):
    headers, _ = create_user_and_auth(client, "notfound@example.com")
    unknown_id = uuid.uuid4()

    res = client.get(f"/api/v1/companies/{unknown_id}/intelligence", headers=headers)
    assert res.status_code == 404


def test_company_intelligence_unauthorized_access(client: TestClient, db_session: Session):
    dummy_id = uuid.uuid4()
    res = client.get(f"/api/v1/companies/{dummy_id}/intelligence")
    assert res.status_code == 401
