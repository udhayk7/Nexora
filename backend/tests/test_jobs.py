from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.audit import audit_service
from app.core.job_utils import (
    canonicalize_job_url,
    compute_canonical_url_hash,
    normalize_job_title,
)
from app.models.company import Company
from app.models.user import User


class MemoryAuditSink:
    """In-memory capture sink for audit events in tests."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


@pytest.fixture
def auth_headers_user1(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "job_user1@example.com",
            "password": "Password123!",
            "full_name": "Job User 1",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "job_user2@example.com",
            "password": "Password123!",
            "full_name": "Job User 2",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(client: TestClient, db_session: Any) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "job_admin@example.com",
            "password": "Password123!",
            "full_name": "Job Admin",
        },
    )
    token = res.json()["access_token"]
    user = db_session.query(User).filter(User.email == "job_admin@example.com").first()
    user.is_superuser = True
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_company(db_session: Any) -> Company:
    comp = Company(
        name="Stripe Payments India",
        normalized_name="stripe payments",
        website_url="https://stripe.com",
        normalized_domain="stripe.com",
        category="product_company",
        headquarters_country="India",
        headquarters_city="Bengaluru",
        verification_status="verified",
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)
    return comp


# 1. Normalization & Canonicalization Unit Tests
def test_canonicalize_job_url_strips_tracking() -> None:
    raw = "https://www.stripe.com/jobs/12345?utm_source=linkedin&utm_campaign=campus&ref=job_board"
    canonical = canonicalize_job_url(raw)
    assert canonical == "https://stripe.com/jobs/12345"

    h1 = compute_canonical_url_hash(raw)
    h2 = compute_canonical_url_hash("https://stripe.com/jobs/12345")
    assert h1 == h2
    assert h1 is not None


def test_normalize_job_title_clustering() -> None:
    assert (
        normalize_job_title("Senior Software Engineer - Backend (Python)")
        == "senior software engineer backend python"
    )
    assert (
        normalize_job_title("Software Development Engineer II") == "software development engineer 2"
    )
    assert normalize_job_title("Frontend Engineer III") == "frontend engineer 3"


# 2. Job Creation & Audit Tests
def test_create_job_success(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    sample_company: Company,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    payload = {
        "title": "Junior Backend Engineer",
        "description": "Build high-throughput payment settlement APIs using Python and FastAPI.",
        "company_id": str(sample_company.id),
        "employment_type": "full_time",
        "seniority_level": "entry_level",
        "work_arrangement": "hybrid",
        "location_text": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "remote_eligibility_regions": ["India"],
        "skills_tags": ["Python", "FastAPI", "PostgreSQL"],
        "role_family": "backend_engineer",
        "salary_min": 1200000.0,
        "salary_max": 1600000.0,
        "salary_currency": "INR",
        "salary_period": "annual",
        "job_url": "https://stripe.com/jobs/junior-backend",
        "initial_source": {
            "source_name": "Official Careers Page",
            "source_type": "careers_page",
            "source_url": "https://stripe.com/jobs/junior-backend",
            "evidence_summary": "Direct listing on Stripe engineering board.",
        },
    }

    res = client.post("/api/v1/jobs", json=payload, headers=auth_headers_user1)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Junior Backend Engineer"
    assert data["normalized_title"] == "junior backend engineer"
    assert data["company_id"] == str(sample_company.id)
    assert data["company"]["name"] == "Stripe Payments India"
    assert data["salary_min"] == 1200000.0
    assert data["salary_currency"] == "INR"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_name"] == "Official Careers Page"

    created_events = [e for e in sink.events if e.action == "job.created"]
    assert len(created_events) == 1
    assert created_events[0].resource_id == data["id"]


# 3. Company Association & Unassociated Handling
def test_company_auto_association(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    sample_company: Company,
) -> None:
    # 1. Matches via domain in job_url
    res1 = client.post(
        "/api/v1/jobs",
        json={
            "title": "Infrastructure Engineer I",
            "description": "Cloud platform engineer working on Kubernetes clusters.",
            "job_url": "https://stripe.com/careers/infra-1?utm_source=twitter",
        },
        headers=auth_headers_user1,
    )
    assert res1.status_code == 201
    assert res1.json()["company_id"] == str(sample_company.id)

    # 2. Unmatched domain and unknown company hint remains unassociated (None)
    res2 = client.post(
        "/api/v1/jobs",
        json={
            "title": "Embedded Systems Engineer",
            "description": "C++ development on microcontrollers.",
            "job_url": "https://unknown-startup-labs.io/jobs/embedded",
            "company_name": "Mysterious Hardware Co",
        },
        headers=auth_headers_user1,
    )
    assert res2.status_code == 201
    assert res2.json()["company_id"] is None
    assert res2.json()["company"] is None


# 4. Duplicate Detection Tests
def test_duplicate_detection(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    sample_company: Company,
) -> None:
    client.post(
        "/api/v1/jobs",
        json={
            "title": "Data Analyst (Early Career)",
            "description": "SQL and Python pipeline analytics.",
            "company_id": str(sample_company.id),
            "job_url": "https://stripe.com/jobs/data-analyst",
        },
        headers=auth_headers_user1,
    )

    # Check identical canonical URL (High confidence)
    dup_res = client.get(
        "/api/v1/jobs/duplicates/check",
        params={"job_url": "https://www.stripe.com/jobs/data-analyst?ref=campus"},
        headers=auth_headers_user1,
    )
    assert dup_res.status_code == 200
    matches = dup_res.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["confidence"] == "high"

    # Check same company + title match (Medium confidence)
    dup_res2 = client.get(
        "/api/v1/jobs/duplicates/check",
        params={
            "job_url": "https://different-mirror-feed.org/job/999",
            "title": "Data Analyst Early Career",
            "company_id": str(sample_company.id),
        },
        headers=auth_headers_user1,
    )
    assert dup_res2.status_code == 200
    matches2 = dup_res2.json()["matches"]
    assert any(m["confidence"] == "medium" for m in matches2)


# 5. Search, Filter, and Pagination Tests
def test_list_and_filter_jobs(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    sample_company: Company,
) -> None:
    # Seed 3 jobs
    jobs = [
        {
            "title": "React Frontend Developer",
            "description": "Build user interfaces with Next.js and TypeScript.",
            "company_id": str(sample_company.id),
            "work_arrangement": "remote",
            "role_family": "frontend_engineer",
            "skills_tags": ["React", "TypeScript"],
            "city": "Kochi",
            "country": "India",
            "job_url": "https://stripe.com/jobs/react-fe",
        },
        {
            "title": "Site Reliability Engineer",
            "description": "Maintain Terraform configurations and observability systems.",
            "company_id": str(sample_company.id),
            "work_arrangement": "onsite",
            "role_family": "devops_cloud",
            "skills_tags": ["AWS", "Terraform"],
            "city": "Bengaluru",
            "country": "India",
            "job_url": "https://stripe.com/jobs/sre-blr",
        },
    ]
    for j in jobs:
        client.post("/api/v1/jobs", json=j, headers=auth_headers_user1)

    # Filter by role_family
    res = client.get(
        "/api/v1/jobs",
        params={"role_family": "frontend_engineer"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(item["title"] == "React Frontend Developer" for item in items)
    assert all(item["role_family"] == "frontend_engineer" for item in items)

    # Filter by work_arrangement
    res_remote = client.get(
        "/api/v1/jobs",
        params={"work_arrangement": "remote"},
        headers=auth_headers_user1,
    )
    assert res_remote.status_code == 200
    assert all(i["work_arrangement"] == "remote" for i in res_remote.json()["items"])

    # Filter by skills tag
    res_skill = client.get(
        "/api/v1/jobs",
        params={"skills": "Terraform"},
        headers=auth_headers_user1,
    )
    assert res_skill.status_code == 200
    assert any(i["title"] == "Site Reliability Engineer" for i in res_skill.json()["items"])


# 6. Verification Status & Evidence Enforcement
def test_verify_job_evidence_requirement(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "QA Automation Engineer",
            "description": "Develop end-to-end Cypress tests for web applications.",
            "job_url": "https://qa-company.io/jobs/1",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    # Fails when verification_notes is empty
    fail_res = client.post(
        f"/api/v1/jobs/{job_id}/verify",
        json={"verification_status": "verified", "verification_notes": ""},
        headers=auth_headers_user1,
    )
    assert fail_res.status_code in {400, 422}

    # Succeeds with evidence notes
    ok_res = client.post(
        f"/api/v1/jobs/{job_id}/verify",
        json={
            "verification_status": "verified",
            "verification_notes": "Active listing confirmed on employer's official careers portal.",
        },
        headers=auth_headers_user1,
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["verification_status"] == "verified"
    assert ok_res.json()["last_verified_at"] is not None

    events = [e for e in sink.events if e.action == "job.verified"]
    assert len(events) == 1


# 7. Job Sources Lifecycle
def test_job_sources_lifecycle(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Security Analyst",
            "description": "Perform vulnerability scans and audits.",
            "job_url": "https://sec-firm.com/jobs/analyst",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    # Add source
    add_src = client.post(
        f"/api/v1/jobs/{job_id}/sources",
        json={
            "source_name": "University Campus Placement Cell",
            "source_type": "other",
            "evidence_summary": "Direct notification from campus placement drive.",
        },
        headers=auth_headers_user1,
    )
    assert add_src.status_code == 201
    source_id = add_src.json()["id"]

    # Check detail has source
    detail = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_user1).json()
    assert any(s["id"] == source_id for s in detail["sources"])

    # Delete source
    del_res = client.delete(
        f"/api/v1/jobs/{job_id}/sources/{source_id}",
        headers=auth_headers_user1,
    )
    assert del_res.status_code == 204


# 8. Batch Feed Ingestion & Idempotency
def test_feed_batch_ingestion_idempotency(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    feed_payload = {
        "feed_name": "TechCampus Public Feed 2026",
        "source_type": "permitted_feed",
        "source_url": "https://techcampus.org/feed.json",
        "records": [
            {
                "title": "Junior Python Developer",
                "description": "Backend services using Flask and PostgreSQL.",
                "job_url": "https://startup-alpha.io/careers/python",
                "external_source_id": "alpha-101",
            },
            {
                "title": "Associate Cloud Engineer",
                "description": "AWS infrastructure provisioning with Terraform.",
                "job_url": "https://startup-beta.io/careers/cloud",
                "external_source_id": "beta-202",
            },
        ],
    }

    # 1. First ingestion -> creates 2 records
    res1 = client.post("/api/v1/jobs/ingest/feed", json=feed_payload, headers=auth_headers_user1)
    assert res1.status_code == 200
    assert res1.json()["created_count"] == 2
    assert res1.json()["updated_count"] == 0

    # 2. Second identical ingestion -> updates existing records idempotently (0 created, 2 updated)
    res2 = client.post("/api/v1/jobs/ingest/feed", json=feed_payload, headers=auth_headers_user1)
    assert res2.status_code == 200
    assert res2.json()["created_count"] == 0
    assert res2.json()["updated_count"] == 2

    # Check audit event
    feed_events = [e for e in sink.events if e.action == "job.feed_ingested"]
    assert len(feed_events) == 2


# 9. Authorization and Scoping
def test_authorization_user_scoping(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
    auth_headers_admin: dict[str, str],
    db_session: Any,
) -> None:
    # User 1 creates job
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Private User 1 Role",
            "description": "Internal test posting.",
            "job_url": "https://user1-test.io/role",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    # User 2 cannot edit User 1's job
    edit_fail = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Hacked Title"},
        headers=auth_headers_user2,
    )
    assert edit_fail.status_code == 403

    # Admin CAN update User 1's job
    admin_ok = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Curated Admin Title"},
        headers=auth_headers_admin,
    )
    assert admin_ok.status_code == 200
    assert admin_ok.json()["title"] == "Curated Admin Title"
