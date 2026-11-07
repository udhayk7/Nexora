import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.user import User
from app.services.job_service import compute_job_freshness


@pytest.fixture
def auth_headers_user1(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify_user1@example.com",
            "password": "Password123!",
            "full_name": "Verify User 1",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify_user2@example.com",
            "password": "Password123!",
            "full_name": "Verify User 2",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(client: TestClient, db_session: Any) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "verify_admin@example.com",
            "password": "Password123!",
            "full_name": "Verify Admin",
        },
    )
    token = res.json()["access_token"]
    user = db_session.query(User).filter(User.email == "verify_admin@example.com").first()
    user.is_superuser = True
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


# 1. Unit Tests for Freshness Computation
def test_compute_job_freshness_tiers() -> None:
    now = datetime.now(timezone.utc)

    assert compute_job_freshness(None) == "unknown"
    assert compute_job_freshness(now) == "recent"
    assert compute_job_freshness(now - timedelta(days=3)) == "recent"
    assert compute_job_freshness(now - timedelta(days=6, hours=12)) == "recent"
    assert compute_job_freshness(now - timedelta(days=8)) == "due_for_review"
    assert compute_job_freshness(now - timedelta(days=13)) == "due_for_review"
    assert compute_job_freshness(now - timedelta(days=15)) == "stale"
    assert compute_job_freshness(now - timedelta(days=90)) == "stale"


# 2. Verification History Creation on Job Verification
def test_verify_job_creates_history_record(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_payload = {
        "title": "Cloud Platform Engineer",
        "description": "Building next generation cloud infrastructure and Kubernetes operators.",
        "job_url": "https://example.com/careers/cloud-engineer",
        "work_arrangement": "remote",
    }
    create_res = client.post("/api/v1/jobs", json=j_payload, headers=auth_headers_user1)
    assert create_res.status_code == 201
    job_id = create_res.json()["id"]

    notes = "Confirmed active listing on employer's authentic careers page with matching role ID."
    verify_res = client.post(
        f"/api/v1/jobs/{job_id}/verify",
        json={
            "verification_status": "verified",
            "verification_notes": notes,
        },
        headers=auth_headers_user1,
    )
    assert verify_res.status_code == 200
    detail = verify_res.json()
    assert detail["verification_status"] == "verified"
    assert len(detail["verification_history"]) == 1
    vh = detail["verification_history"][0]
    assert vh["verifier_type"] == "user"
    assert vh["verification_outcome"] == "verified"
    assert vh["reason"] == notes

    hist_res = client.get(f"/api/v1/jobs/{job_id}/verifications", headers=auth_headers_user1)
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) == 1
    assert hist[0]["job_id"] == job_id


# 3. Manual Evidence Submission & Multi-event Chronological Persistence
def test_submit_verification_evidence_multi_event(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_payload = {
        "title": "Junior Data Engineer",
        "description": "ETL pipelines using Python, SQL, and Apache Airflow.",
        "job_url": "https://example.com/careers/data-eng",
    }
    j_res = client.post("/api/v1/jobs", json=j_payload, headers=auth_headers_user1)
    job_id = j_res.json()["id"]

    # First verification: corroborated
    ev1 = {
        "evidence_type": "careers_page",
        "evidence_url": "https://example.com/careers/data-eng",
        "evidence_summary": "Active job post verified on public career portal.",
        "observed_status": "active",
        "verification_outcome": "corroborated",
        "reason": "Direct listing verified on primary company careers portal.",
    }
    res1 = client.post(f"/api/v1/jobs/{job_id}/verifications", json=ev1, headers=auth_headers_user1)
    assert res1.status_code == 201
    d1 = res1.json()
    assert d1["verification_status"] == "corroborated"
    assert len(d1["verification_history"]) == 1

    # Second verification: listing closed
    ev2 = {
        "evidence_type": "user_evidence",
        "evidence_url": "https://example.com/careers/data-eng",
        "evidence_summary": "Employer posting states applications are no longer accepted.",
        "observed_status": "closed",
        "verification_outcome": "expired",
        "reason": "Employer notice indicates candidate pool is closed.",
    }
    res2 = client.post(f"/api/v1/jobs/{job_id}/verifications", json=ev2, headers=auth_headers_user1)
    assert res2.status_code == 201
    d2 = res2.json()
    assert d2["verification_status"] == "expired"
    assert d2["job_status"] == "closed"
    assert len(d2["verification_history"]) == 2

    # Check history order: latest first
    hist_res = client.get(f"/api/v1/jobs/{job_id}/verifications", headers=auth_headers_user1)
    assert hist_res.status_code == 200
    items = hist_res.json()
    assert len(items) == 2
    assert items[0]["verification_outcome"] == "expired"
    assert items[1]["verification_outcome"] == "corroborated"


# 4. Validation Errors on Evidence Submission
def test_submit_verification_validation(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend QA Specialist",
            "description": "Integration and end-to-end testing with Pytest.",
            "job_url": "https://example.com/jobs/qa",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    # Fails if reason is too short (< 5 chars)
    short_reason = {
        "evidence_type": "user_evidence",
        "observed_status": "active",
        "verification_outcome": "verified",
        "reason": "ok",
    }
    res_short = client.post(
        f"/api/v1/jobs/{job_id}/verifications", json=short_reason, headers=auth_headers_user1
    )
    assert res_short.status_code in {400, 422}

    # Fails if evidence_url is private/restricted IP (SSRF guard)
    ssrf_url = {
        "evidence_type": "user_evidence",
        "evidence_url": "http://127.0.0.1:8000/internal",
        "observed_status": "active",
        "verification_outcome": "verified",
        "reason": "Checking local host port directly.",
    }
    res_ssrf = client.post(
        f"/api/v1/jobs/{job_id}/verifications", json=ssrf_url, headers=auth_headers_user1
    )
    assert res_ssrf.status_code in {400, 422}


# 5. Automated Recheck - Reachable URL (HTTP 200)
def test_recheck_job_active(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Frontend Architect",
            "description": "Design design systems and microfrontend architecture in TypeScript.",
            "job_url": "https://example.com/jobs/frontend-arch",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    with patch(
        "app.services.job_service.safe_check_url_status",
        return_value=(True, 200, "URL active and reachable (HTTP 200)"),
    ):
        recheck_res = client.post(
            f"/api/v1/jobs/{job_id}/recheck",
            json={"force_remote_check": True},
            headers=auth_headers_user1,
        )
        assert recheck_res.status_code == 200
        data = recheck_res.json()
        assert data["recheck_status"] == "completed"
        assert data["observed_status"] == "active"
        assert data["freshness"] == "recent"
        assert data["status_code"] == 200
        assert data["verification"] is not None
        assert data["verification"]["verifier_type"] == "system"


# 6. Automated Recheck - Missing/Removed Listing (HTTP 404)
def test_recheck_job_removed(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Junior DevOps Engineer",
            "description": "CI/CD pipelines with GitHub Actions and Terraform.",
            "job_url": "https://example.com/jobs/junior-devops",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    with patch(
        "app.services.job_service.safe_check_url_status",
        return_value=(False, 404, "Listing not found (HTTP 404)"),
    ):
        recheck_res = client.post(
            f"/api/v1/jobs/{job_id}/recheck",
            json={"force_remote_check": True},
            headers=auth_headers_user1,
        )
        assert recheck_res.status_code == 200
        data = recheck_res.json()
        assert data["recheck_status"] == "completed"
        assert data["observed_status"] == "removed"
        assert data["status_code"] == 404

        detail_res = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_user1)
        assert detail_res.json()["job_status"] == "closed"


# 7. Automated Recheck - SSRF Block Handling
def test_recheck_job_blocked_ssrf(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Security Analyst",
            "description": "Vulnerability assessment and application security reviews.",
            "job_url": "https://example.com/jobs/sec-analyst",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    with patch(
        "app.services.job_service.safe_check_url_status",
        return_value=(
            False,
            None,
            "Security alert: Target URL resolves to a private or restricted network address",
        ),
    ):
        recheck_res = client.post(
            f"/api/v1/jobs/{job_id}/recheck",
            json={"force_remote_check": True},
            headers=auth_headers_user1,
        )
        assert recheck_res.status_code == 200
        data = recheck_res.json()
        assert data["recheck_status"] == "failed"
        assert data["observed_status"] == "unknown"

        detail_res = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_user1)
        assert detail_res.json()["verification_status"] == "suspicious"


# 8. Automated Recheck - Inconclusive Remote Response
def test_recheck_job_inconclusive(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Mobile Developer",
            "description": "iOS and Android apps with React Native.",
            "job_url": "https://example.com/jobs/mobile-dev",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    with patch(
        "app.services.job_service.safe_check_url_status",
        return_value=(False, 503, "URL returned HTTP 503"),
    ):
        recheck_res = client.post(
            f"/api/v1/jobs/{job_id}/recheck",
            json={"force_remote_check": True},
            headers=auth_headers_user1,
        )
        assert recheck_res.status_code == 200
        data = recheck_res.json()
        assert data["recheck_status"] == "manual_evidence_required"
        assert data["observed_status"] == "unknown"


# 9. Authorization Checks - Regular User vs Owner vs Superuser
def test_verification_authorization_rules(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
    auth_headers_admin: dict[str, str],
) -> None:
    j_res = client.post(
        "/api/v1/jobs",
        json={
            "title": "Proprietary Backend Developer",
            "description": "Internal systems engineering with FastAPI and Celery.",
            "job_url": "https://example.com/jobs/prop-dev",
        },
        headers=auth_headers_user1,
    )
    job_id = j_res.json()["id"]

    # User 2 tries to submit verification on User 1's job -> 403 Forbidden
    unauth_res = client.post(
        f"/api/v1/jobs/{job_id}/verifications",
        json={
            "evidence_type": "user_evidence",
            "observed_status": "active",
            "verification_outcome": "verified",
            "reason": "I think this listing looks authentic.",
        },
        headers=auth_headers_user2,
    )
    assert unauth_res.status_code == 403

    # Superuser can verify and manage any job
    admin_res = client.post(
        f"/api/v1/jobs/{job_id}/verifications",
        json={
            "evidence_type": "user_evidence",
            "observed_status": "active",
            "verification_outcome": "verified",
            "reason": "Administrative verification conducted on company portal.",
        },
        headers=auth_headers_admin,
    )
    assert admin_res.status_code == 201
    assert admin_res.json()["verification_status"] == "verified"


# 10. Filter Jobs by Freshness Tier
def test_list_jobs_freshness_filter(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    db_session: Session,
) -> None:
    j1 = client.post(
        "/api/v1/jobs",
        json={
            "title": "Fresh Job Position",
            "description": "Very recent position check.",
            "job_url": "https://example.com/jobs/fresh-pos",
        },
        headers=auth_headers_user1,
    ).json()

    j2 = client.post(
        "/api/v1/jobs",
        json={
            "title": "Stale Job Position",
            "description": "Older position check.",
            "job_url": "https://example.com/jobs/stale-pos",
        },
        headers=auth_headers_user1,
    ).json()

    # Artificially age j2's last_checked_at in DB
    stale_job = db_session.query(Job).filter(Job.id == uuid.UUID(j2["id"])).first()
    assert stale_job is not None
    stale_job.last_checked_at = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.commit()

    # Query freshness=recent
    res_recent = client.get("/api/v1/jobs?freshness=recent", headers=auth_headers_user1)
    assert res_recent.status_code == 200
    recent_ids = [item["id"] for item in res_recent.json()["items"]]
    assert j1["id"] in recent_ids
    assert j2["id"] not in recent_ids

    # Query freshness=stale
    res_stale = client.get("/api/v1/jobs?freshness=stale", headers=auth_headers_user1)
    assert res_stale.status_code == 200
    stale_ids = [item["id"] for item in res_stale.json()["items"]]
    assert j2["id"] in stale_ids
    assert j1["id"] not in stale_ids
