import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.audit import audit_service
from app.core.errors import BadRequestError
from app.core.url_validator import (
    extract_normalized_domain,
    normalize_company_name,
    validate_safe_url,
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
            "email": "company_user1@example.com",
            "password": "Password123!",
            "full_name": "Company User 1",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "company_user2@example.com",
            "password": "Password123!",
            "full_name": "Company User 2",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(client: TestClient, db_session: Any) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "company_admin@example.com",
            "password": "Password123!",
            "full_name": "Company Admin",
        },
    )
    token = res.json()["access_token"]
    user = db_session.query(User).filter(User.email == "company_admin@example.com").first()
    user.is_superuser = True
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


# 1. URL Validation & SSRF Guard Unit Tests
def test_normalize_company_name() -> None:
    assert normalize_company_name("Acme Technologies, Inc.") == "acme"
    assert normalize_company_name("Google LLC") == "google"
    assert normalize_company_name("Stripe, Inc.") == "stripe"
    assert normalize_company_name("Freshworks Pvt. Ltd.") == "freshworks"


def test_extract_normalized_domain() -> None:
    assert extract_normalized_domain("https://www.google.com/careers") == "google.com"
    assert extract_normalized_domain("http://stripe.com/jobs/") == "stripe.com"
    assert extract_normalized_domain("https://sub.domain.co.uk") == "sub.domain.co.uk"
    assert extract_normalized_domain(None) is None


def test_validate_safe_url_ssrf_protection() -> None:
    # Valid external URLs
    assert validate_safe_url("https://example.com/careers") == "https://example.com/careers"
    assert validate_safe_url("http://github.com") == "http://github.com"
    assert validate_safe_url(None) is None

    # Invalid protocols
    with pytest.raises(BadRequestError):
        validate_safe_url("ftp://example.com")
    with pytest.raises(BadRequestError):
        validate_safe_url("file:///etc/passwd")

    # SSRF Loopback & private IP ranges
    with pytest.raises(BadRequestError):
        validate_safe_url("http://127.0.0.1:8000")
    with pytest.raises(BadRequestError):
        validate_safe_url("http://localhost:3000")
    with pytest.raises(BadRequestError):
        validate_safe_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(BadRequestError):
        validate_safe_url("http://10.0.0.1/admin")
    with pytest.raises(BadRequestError):
        validate_safe_url("http://192.168.1.1/setup")


# 2. Company Registration & Audit Tests
def test_create_company_success(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    payload = {
        "name": "Nexa Systems, Inc.",
        "category": "product_company",
        "website_url": "https://nexasystems.io",
        "careers_url": "https://nexasystems.io/careers",
        "headquarters_country": "India",
        "headquarters_city": "Bengaluru",
        "operating_regions": ["India", "Singapore", "United States"],
        "industry_tags": ["DevTools", "Cloud Infrastructure"],
        "technology_tags": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "size_band": "51-200",
        "description": "Developer platform for distributed observability.",
        "initial_source": {
            "source_name": "Direct Careers Portal",
            "source_type": "official_website",
            "source_url": "https://nexasystems.io/careers",
            "evidence_summary": "Active campus hiring page observed.",
        },
    }

    res = client.post("/api/v1/companies", json=payload, headers=auth_headers_user1)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Nexa Systems, Inc."
    assert data["normalized_name"] == "nexa"
    assert data["normalized_domain"] == "nexasystems.io"
    assert data["verification_status"] == "unverified"
    assert data["category"] == "product_company"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_name"] == "Direct Careers Portal"

    # Verify audit event
    created_events = [e for e in sink.events if e.action == "company.created"]
    assert len(created_events) == 1
    assert created_events[0].resource_id == data["id"]
    assert created_events[0].metadata["company_name"] == "Nexa Systems, Inc."


# 3. Duplicate Detection Tests
def test_duplicate_detection(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    # First create a baseline company
    client.post(
        "/api/v1/companies",
        json={
            "name": "Acme Technologies Corp",
            "category": "product_company",
            "website_url": "https://acme-tools.com",
        },
        headers=auth_headers_user1,
    )

    # Check identical domain (High confidence)
    res = client.get(
        "/api/v1/companies/duplicates/check",
        params={"name": "Completely Different Name", "website_url": "https://acme-tools.com/jobs"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    matches = res.json()["matches"]
    assert len(matches) == 1
    assert matches[0]["confidence"] == "high"

    # Check similar normalized name (Medium confidence)
    res = client.get(
        "/api/v1/companies/duplicates/check",
        params={"name": "Acme Technologies, Inc.", "website_url": "https://other-domain.io"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    matches = res.json()["matches"]
    assert any(m["confidence"] == "medium" for m in matches)

    # Check no match
    res = client.get(
        "/api/v1/companies/duplicates/check",
        params={"name": "Unique Brand New Entity", "website_url": "https://brandnew.com"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    assert len(res.json()["matches"]) == 0


# 4. Search, Filter, and Pagination Tests
def test_list_and_filter_companies(
    client: TestClient,
    auth_headers_user1: dict[str, str],
) -> None:
    # Seed 3 distinct companies
    companies_data = [
        {
            "name": "Alpha GCC Services",
            "category": "gcc",
            "headquarters_country": "India",
            "headquarters_city": "Hyderabad",
            "operating_regions": ["India"],
            "industry_tags": ["Banking", "Finance"],
            "technology_tags": ["Java", "Spring Boot"],
        },
        {
            "name": "Beta Big Four Consulting",
            "category": "big_four",
            "headquarters_country": "United Kingdom",
            "headquarters_city": "London",
            "operating_regions": ["Global", "India"],
            "industry_tags": ["Audit", "Advisory"],
            "technology_tags": ["Python", "Azure"],
        },
        {
            "name": "Gamma AI Labs",
            "category": "established_startup",
            "headquarters_country": "United States",
            "headquarters_city": "San Francisco",
            "operating_regions": ["United States", "India"],
            "industry_tags": ["Artificial Intelligence"],
            "technology_tags": ["Python", "PyTorch", "Rust"],
        },
    ]
    for c in companies_data:
        client.post("/api/v1/companies", json=c, headers=auth_headers_user1)

    # Filter by category
    res = client.get(
        "/api/v1/companies",
        params={"category": "gcc"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(item["name"] == "Alpha GCC Services" for item in items)
    assert all(item["category"] == "gcc" for item in items)

    # Filter by technology tag
    res = client.get(
        "/api/v1/companies",
        params={"technology": "PyTorch"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Gamma AI Labs"

    # Filter by region
    res = client.get(
        "/api/v1/companies",
        params={"region": "Hyderabad"},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(item["name"] == "Alpha GCC Services" for item in items)

    # Pagination test
    res = client.get(
        "/api/v1/companies",
        params={"page": 1, "per_page": 2},
        headers=auth_headers_user1,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) <= 2
    assert data["per_page"] == 2


# 5. Verification State Transition & Evidence Tests
def test_verification_status_requires_evidence(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    res = client.post(
        "/api/v1/companies",
        json={"name": "Delta Tech", "category": "product_company"},
        headers=auth_headers_user1,
    )
    comp_id = res.json()["id"]

    # Attempt to mark verified without evidence notes
    fail_res = client.post(
        f"/api/v1/companies/{comp_id}/verify",
        json={"verification_status": "verified", "verification_notes": ""},
        headers=auth_headers_user1,
    )
    assert fail_res.status_code == 422  # Pydantic min_length validation

    fail_res2 = client.post(
        f"/api/v1/companies/{comp_id}/verify",
        json={"verification_status": "verified", "verification_notes": "   "},
        headers=auth_headers_user1,
    )
    assert fail_res2.status_code in {400, 422}

    # Verify with valid evidence notes
    ok_res = client.post(
        f"/api/v1/companies/{comp_id}/verify",
        json={
            "verification_status": "verified",
            "verification_notes": "Corroborated with active Ministry of Corporate Affairs filing.",
        },
        headers=auth_headers_user1,
    )
    assert ok_res.status_code == 200
    data = ok_res.json()
    assert data["verification_status"] == "verified"
    assert "Ministry of Corporate Affairs" in data["verification_notes"]
    assert data["last_verified_at"] is not None

    verified_events = [e for e in sink.events if e.action == "company.verified"]
    assert len(verified_events) == 1


# 6. Discovery Sources Provenance Lifecycle
def test_company_sources_lifecycle(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    c_res = client.post(
        "/api/v1/companies",
        json={"name": "Epsilon Cloud", "category": "product_company"},
        headers=auth_headers_user1,
    )
    comp_id = c_res.json()["id"]

    # Add source
    src_payload = {
        "source_name": "Public Seed Directory 2026",
        "source_type": "public_directory",
        "source_url": "https://public-directory.org/epsilon",
        "evidence_summary": "Listed under verified early stage tech startups.",
    }
    add_res = client.post(
        f"/api/v1/companies/{comp_id}/sources",
        json=src_payload,
        headers=auth_headers_user1,
    )
    assert add_res.status_code == 201
    source_id = add_res.json()["id"]

    # Update source
    update_res = client.patch(
        f"/api/v1/companies/{comp_id}/sources/{source_id}",
        json={"evidence_summary": "Updated after cross-checking directory listing."},
        headers=auth_headers_user1,
    )
    assert update_res.status_code == 200
    assert "cross-checking" in update_res.json()["evidence_summary"]

    # Detail check
    detail_res = client.get(f"/api/v1/companies/{comp_id}", headers=auth_headers_user1)
    sources = detail_res.json()["sources"]
    assert any(s["id"] == source_id for s in sources)

    # Delete source
    del_res = client.delete(
        f"/api/v1/companies/{comp_id}/sources/{source_id}",
        headers=auth_headers_user1,
    )
    assert del_res.status_code == 204

    # Detail check after deletion
    detail_res2 = client.get(f"/api/v1/companies/{comp_id}", headers=auth_headers_user1)
    assert not any(s["id"] == source_id for s in detail_res2.json()["sources"])


# 7. Explicit Merge Tests
def test_explicit_merge_companies(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    # Create target company
    target_res = client.post(
        "/api/v1/companies",
        json={
            "name": "Zeta Global Technologies",
            "category": "mnc",
            "headquarters_city": "Munich",
            "technology_tags": ["C++", "Python"],
        },
        headers=auth_headers_user1,
    )
    target_id = target_res.json()["id"]

    # Create secondary duplicate company with distinct tags and sources
    sec_res = client.post(
        "/api/v1/companies",
        json={
            "name": "Zeta Technologies GmbH",
            "category": "mnc",
            "website_url": "https://zeta-global.de",
            "careers_url": "https://zeta-global.de/jobs",
            "description": "European arm specializing in embedded software.",
            "technology_tags": ["Python", "Rust"],
            "industry_tags": ["Embedded", "IoT"],
            "initial_source": {
                "source_name": "Regional German Registry",
                "source_type": "public_directory",
                "evidence_summary": "Confirmed legal German entity.",
            },
        },
        headers=auth_headers_user1,
    )
    secondary_id = sec_res.json()["id"]

    # Perform explicit merge
    merge_res = client.post(
        f"/api/v1/companies/{target_id}/merge",
        json={
            "secondary_company_id": secondary_id,
            "merge_reason": "Consolidation of regional entity into global parent record.",
        },
        headers=auth_headers_user1,
    )
    assert merge_res.status_code == 200
    merged_data = merge_res.json()

    # Check target received missing attributes
    assert merged_data["careers_url"] == "https://zeta-global.de/jobs"
    assert merged_data["website_url"] == "https://zeta-global.de"
    assert "embedded software" in merged_data["description"].lower()

    # Check merged tags
    tech_tags = set(merged_data["technology_tags"])
    assert {"C++", "Python", "Rust"}.issubset(tech_tags)
    ind_tags = set(merged_data["industry_tags"])
    assert {"Embedded", "IoT"}.issubset(ind_tags)

    # Check transferred sources
    source_names = [s["source_name"] for s in merged_data["sources"]]
    assert "Regional German Registry" in source_names

    # Verify secondary company cannot be merged again or listed
    list_res = client.get("/api/v1/companies", headers=auth_headers_user1)
    active_ids = [c["id"] for c in list_res.json()["items"]]
    assert secondary_id not in active_ids

    # Check audit event
    merge_events = [e for e in sink.events if e.action == "company.merged"]
    assert len(merge_events) == 1
    assert merge_events[0].resource_id == target_id
    assert merge_events[0].metadata["secondary_company_id"] == secondary_id


# 8. User Authorization & Global Scoping Tests
def test_authorization_user_isolation_and_admin(
    client: TestClient,
    auth_headers_user1: dict[str, str],
    auth_headers_user2: dict[str, str],
    auth_headers_admin: dict[str, str],
    db_session: Any,
) -> None:
    # User 1 creates a company
    res1 = client.post(
        "/api/v1/companies",
        json={"name": "User 1 Secret Labs", "category": "product_company"},
        headers=auth_headers_user1,
    )
    comp1_id = res1.json()["id"]

    # User 2 cannot edit User 1's company
    edit_fail = client.patch(
        f"/api/v1/companies/{comp1_id}",
        json={"description": "Hacked description"},
        headers=auth_headers_user2,
    )
    assert edit_fail.status_code == 403

    # User 2 cannot verify User 1's company
    verify_fail = client.post(
        f"/api/v1/companies/{comp1_id}/verify",
        json={"verification_status": "verified", "verification_notes": "Unauthorized note"},
        headers=auth_headers_user2,
    )
    assert verify_fail.status_code == 403

    # Admin CAN update User 1's company
    admin_ok = client.patch(
        f"/api/v1/companies/{comp1_id}",
        json={"description": "Admin curated description"},
        headers=auth_headers_admin,
    )
    assert admin_ok.status_code == 200
    assert admin_ok.json()["description"] == "Admin curated description"

    # Global company can only be modified by admin
    comp = db_session.query(Company).filter(Company.id == uuid.UUID(comp1_id)).first()
    comp.is_global = True
    comp.created_by_user_id = None
    db_session.commit()

    user1_edit_global_fail = client.patch(
        f"/api/v1/companies/{comp1_id}",
        json={"name": "Renamed Global Corp"},
        headers=auth_headers_user1,
    )
    assert user1_edit_global_fail.status_code == 403

    admin_edit_global_ok = client.patch(
        f"/api/v1/companies/{comp1_id}",
        json={"name": "Renamed Global Corp by Admin"},
        headers=auth_headers_admin,
    )
    assert admin_edit_global_ok.status_code == 200
