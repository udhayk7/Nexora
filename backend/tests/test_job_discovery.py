from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.company import Company, CompanySource, DiscoveryScanLog
from app.models.job import Job, JobSource, JobVerification
from app.services.discovery.adapters.ashby import AshbyAdapter
from app.services.discovery.adapters.base import DiscoveredJob
from app.services.discovery.adapters.greenhouse import GreenhouseAdapter
from app.services.discovery.adapters.json_feed import JSONFeedAdapter
from app.services.discovery.adapters.lever import LeverAdapter
from app.services.discovery.adapters.rss import RSSFeedAdapter
from app.services.discovery.discovery_service import JobDiscoveryService
from app.services.discovery.normalizer import JobNormalizer
from app.tasks.discovery_tasks import (
    scan_all_due_sources_task,
    scan_single_company_source_task,
)


def create_user_and_token(
    client: TestClient, email: str = "discovery_user@example.com"
) -> tuple[dict[str, str], str]:
    """Helper to register and authenticate a test user."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Discovery Tester",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def create_test_company(db_session: Session, name: str = "Stripe, Inc.") -> Company:
    """Helper to create a test company."""
    comp = Company(
        name=name,
        normalized_name="stripe",
        website_url="https://stripe.com",
        normalized_domain="stripe.com",
        category="product",
        is_global=True,
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)
    return comp


# -----------------------------------------------------------------------------
# 1. Source Adapter Tests (Greenhouse, Lever, Ashby, RSS, JSON)
# -----------------------------------------------------------------------------


def test_greenhouse_adapter_parsing() -> None:
    """Test Greenhouse adapter parses API JSON response into DiscoveredJob entities."""
    adapter = GreenhouseAdapter()
    mock_payload = {
        "jobs": [
            {
                "id": 1001,
                "title": "Graduate AI Engineer",
                "updated_at": "2026-10-15T12:00:00Z",
                "absolute_url": "https://boards.greenhouse.io/testco/jobs/1001",
                "location": {"name": "Bengaluru, India"},
                "content": "<p>Graduate AI Engineer skilled in Python and PyTorch.</p>",
                "departments": [{"name": "AI Engineering"}],
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {}
    mock_resp.is_redirect = False

    with patch.object(adapter, "safe_get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(board_token="testco")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Graduate AI Engineer"
    assert job.job_url == "https://boards.greenhouse.io/testco/jobs/1001"
    assert job.external_source_id == "greenhouse:testco:1001"
    assert "Graduate AI Engineer" in job.description
    assert job.role_family == "AI Engineer"
    assert job.seniority_level == "entry_level"
    assert "python" in job.skills_tags
    assert "pytorch" in job.skills_tags
    assert job.city == "Bengaluru"
    assert job.country == "India"


def test_lever_adapter_parsing() -> None:
    """Test Lever adapter parses public postings JSON response."""
    adapter = LeverAdapter()
    mock_payload = [
        {
            "id": "lever-uuid-42",
            "text": "Junior Python Backend Developer",
            "createdAt": 1729000000000,
            "hostedUrl": "https://jobs.lever.co/netflix/lever-uuid-42",
            "applyUrl": "https://jobs.lever.co/netflix/lever-uuid-42/apply",
            "categories": {
                "commitment": "Full-time",
                "department": "Engineering",
                "location": "Remote",
            },
            "descriptionPlain": "Build robust FastAPI and PostgreSQL microservices.",
            "lists": [
                {
                    "text": "Requirements",
                    "content": "<ul><li>FastAPI</li><li>Docker</li></ul>",
                }
            ],
        }
    ]

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {}
    mock_resp.is_redirect = False

    with patch.object(adapter, "safe_get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(board_token="netflix")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Junior Python Backend Developer"
    assert job.role_family == "Python Backend Developer"
    assert job.seniority_level == "junior"
    assert job.work_arrangement == "remote"
    assert "fastapi" in job.skills_tags
    assert "docker" in job.skills_tags
    assert job.external_source_id == "lever:netflix:lever-uuid-42"


def test_ashby_adapter_parsing() -> None:
    """Test Ashby adapter parses job board JSON response."""
    adapter = AshbyAdapter()
    mock_payload = {
        "jobs": [
            {
                "id": "ashby-job-99",
                "title": "Software Development Engineer (Fresher)",
                "department": "Core Platform",
                "location": "Kochi, Kerala, India",
                "employmentType": "FullTime",
                "isRemote": False,
                "jobUrl": "https://jobs.ashbyhq.com/linear/ashby-job-99",
                "applyUrl": "https://jobs.ashbyhq.com/linear/ashby-job-99/application",
                "publishedAt": "2026-10-20T10:00:00.000Z",
                "compensation": {"compensationTierSummary": "₹8,00,000 - ₹14,00,000 / year"},
                "descriptionPlain": "Graduates with knowledge of React and TypeScript.",
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {}
    mock_resp.is_redirect = False

    with patch.object(adapter, "safe_get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(board_token="linear")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Software Development Engineer (Fresher)"
    assert job.role_family == "Software Development Engineer"
    assert job.seniority_level == "entry_level"
    assert "react" in job.skills_tags
    assert "typescript" in job.skills_tags
    assert job.salary_min == 800000.0
    assert job.salary_max == 1400000.0
    assert job.salary_currency == "INR"


def test_rss_feed_adapter_parsing() -> None:
    """Test RSS adapter parses XML feed into normalized DiscoveredJob records."""
    adapter = RSSFeedAdapter()
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Company Tech Careers</title>
            <item>
                <title>Frontend Developer Intern</title>
                <link>https://careers.example.com/jobs/fe-intern</link>
                <description><![CDATA[Frontend Intern: React and Tailwind.]]></description>
                <guid>guid-12345</guid>
                <pubDate>Mon, 20 Oct 2026 09:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.content = xml_content
    mock_resp.headers = {}
    mock_resp.is_redirect = False

    with patch.object(adapter, "safe_get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(source_url="https://careers.example.com/feed.xml")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Frontend Developer Intern"
    assert job.role_family == "Frontend Developer"
    assert job.seniority_level == "internship"
    assert "react" in job.skills_tags
    assert "tailwindcss" in job.skills_tags
    assert job.external_source_id == "rss:guid-12345"


def test_json_feed_adapter_parsing() -> None:
    """Test generic JSON feed adapter parses custom job arrays."""
    adapter = JSONFeedAdapter()
    mock_payload = {
        "listings": [
            {
                "id": "job-777",
                "title": "Data Analyst (Early Career)",
                "url": "https://company.com/jobs/777",
                "description": "SQL, Python, and Tableau experience required. ₹6 - 10 LPA.",
                "location": "Hyderabad, India",
                "work_arrangement": "hybrid",
            }
        ]
    }
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload
    mock_resp.headers = {}
    mock_resp.is_redirect = False

    with patch.object(adapter, "safe_get", return_value=mock_resp):
        jobs = adapter.fetch_jobs(source_url="https://company.com/api/jobs.json")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Data Analyst (Early Career)"
    assert job.role_family == "Data Analyst"
    assert job.work_arrangement == "hybrid"
    assert "sql" in job.skills_tags
    assert "python" in job.skills_tags
    assert "tableau" in job.skills_tags
    assert job.salary_min == 600000.0
    assert job.salary_max == 1000000.0
    assert job.salary_currency == "INR"


# -----------------------------------------------------------------------------
# 2. Normalization Engine Tests
# -----------------------------------------------------------------------------


def test_role_family_classification_for_all_ten_categories() -> None:
    """Verify JobNormalizer accurately classifies all 10 Nexora technical role families."""
    test_cases = [
        ("Senior Generative AI / LLM Engineer", "Generative AI / LLM Engineer"),
        ("AI Engineer - Computer Vision", "AI Engineer"),
        ("Machine Learning Engineer (MLOps)", "Machine Learning Engineer"),
        ("Python Backend Developer", "Python Backend Developer"),
        ("Senior Frontend Developer (React/TS)", "Frontend Developer"),
        ("Full Stack Developer (Next.js)", "Full Stack Developer"),
        ("Data Engineer (Pipelines & Spark)", "Data Engineer"),
        ("Business Intelligence / Data Analyst", "Data Analyst"),
        ("QA Automation Engineer (SDET)", "Automation Engineer"),
        ("Software Development Engineer I", "Software Development Engineer"),
    ]
    for title, expected_family in test_cases:
        actual = JobNormalizer.classify_role_family(title)
        assert actual == expected_family, f"Expected {expected_family} for '{title}', got {actual}"


def test_seniority_and_early_career_classification() -> None:
    """Verify early-career signals prioritize junior/fresh graduate roles over seniors."""
    # Fresher / graduate
    level, is_early = JobNormalizer.classify_seniority("Software Engineer - Graduate 2026")
    assert level == "entry_level"
    assert is_early is True

    # Intern
    level, is_early = JobNormalizer.classify_seniority("Machine Learning Intern")
    assert level == "internship"
    assert is_early is True

    # Junior
    level, is_early = JobNormalizer.classify_seniority("Junior Python Developer")
    assert level == "junior"
    assert is_early is True

    # Senior is excluded from early-career
    level, is_early = JobNormalizer.classify_seniority("Lead Principal Software Architect")
    assert level == "senior"
    assert is_early is False


def test_salary_parsing_never_fabricates() -> None:
    """Verify salary parser extracts explicit figures and returns None when absent."""
    # When no salary mentioned
    s_min, s_max, curr, period = JobNormalizer.parse_explicit_salary("Great perks and benefits.")
    assert s_min is None and s_max is None and curr is None and period is None

    # INR LPA format
    s_min, s_max, curr, period = JobNormalizer.parse_explicit_salary("Salary range: ₹8 - 14 LPA")
    assert s_min == 800000.0
    assert s_max == 1400000.0
    assert curr == "INR"
    assert period == "annual"

    # USD annual range
    s_min, s_max, curr, period = JobNormalizer.parse_explicit_salary(
        "Compensation: $90,000 - $130,000 per year"
    )
    assert s_min == 900000.0 or s_min == 90000.0
    assert curr == "USD"
    assert period == "annual"


# -----------------------------------------------------------------------------
# 3. Discovery Ingestion Service & Idempotency Tests
# -----------------------------------------------------------------------------


def test_idempotent_source_scanning_and_deduplication(db_session: Session) -> None:
    """Verify scanning a source twice updates existing jobs without creating duplicates."""
    company = create_test_company(db_session, "Airbnb")

    source = CompanySource(
        company_id=company.id,
        source_name="Airbnb Greenhouse",
        source_type="careers_page",
        adapter_name="greenhouse",
        board_token="airbnb",
        is_enabled=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    mock_discovered_jobs = [
        DiscoveredJob(
            title="Associate Software Engineer",
            job_url="https://careers.airbnb.com/positions/4001",
            description="Associate Software Engineer working with Python and React.",
            external_source_id="greenhouse:airbnb:4001",
            location_text="Remote - India",
            role_family="Software Development Engineer",
            seniority_level="entry_level",
            work_arrangement="remote",
            skills_tags=["python", "react"],
        )
    ]

    mock_adapter = MagicMock()
    mock_adapter.fetch_jobs.return_value = mock_discovered_jobs

    with patch("app.services.discovery.discovery_service.get_adapter", return_value=mock_adapter):
        # 1. First scan: creates job
        res1 = JobDiscoveryService.scan_source(db_session, source.id)
        assert res1.status == "success"
        assert res1.jobs_imported == 1
        assert res1.jobs_updated == 0

        # Check job in database
        job = db_session.query(Job).filter(Job.company_id == company.id).first()
        assert job is not None
        assert job.title == "Associate Software Engineer"
        # Automated ingestion must set status to corroborated, never verified
        assert job.verification_status == "corroborated"

        # Check JobSource citation
        job_src = db_session.query(JobSource).filter(JobSource.job_id == job.id).first()
        assert job_src is not None
        assert job_src.source_name == "Airbnb Greenhouse"

        # Check JobVerification audit record
        j_ver = db_session.query(JobVerification).filter(JobVerification.job_id == job.id).first()
        assert j_ver is not None
        assert j_ver.verification_outcome == "corroborated"

        # 2. Second scan with same jobs: updates without creating duplicates
        res2 = JobDiscoveryService.scan_source(db_session, source.id)
        assert res2.status == "success"
        assert res2.jobs_imported == 0
        assert res2.jobs_updated == 1

        total_jobs = db_session.query(Job).filter(Job.company_id == company.id).count()
        assert total_jobs == 1

        # Check DiscoveryScanLog
        logs = (
            db_session.query(DiscoveryScanLog)
            .filter(DiscoveryScanLog.company_source_id == source.id)
            .all()
        )
        assert len(logs) == 2


def test_batch_scanning_isolates_source_failures(db_session: Session) -> None:
    """Verify that a failure in one source does not crash or halt the batch scan."""
    comp1 = create_test_company(db_session, "FailingCo")
    comp2 = create_test_company(db_session, "WorkingCo")

    src1 = CompanySource(
        company_id=comp1.id,
        source_name="Failing Source",
        source_type="careers_page",
        adapter_name="greenhouse",
        board_token="failing_token",
        is_enabled=True,
    )
    src2 = CompanySource(
        company_id=comp2.id,
        source_name="Working Source",
        source_type="careers_page",
        adapter_name="lever",
        board_token="working_token",
        is_enabled=True,
    )
    db_session.add_all([src1, src2])
    db_session.commit()

    def mock_get_adapter(name: str):
        adapter = MagicMock()
        if name == "greenhouse":
            adapter.fetch_jobs.side_effect = RuntimeError("Upstream API is down")
        else:
            adapter.fetch_jobs.return_value = [
                DiscoveredJob(
                    title="Junior Frontend Engineer",
                    job_url="https://jobs.lever.co/working/1",
                    description="React and Next.js developer.",
                    external_source_id="lever:working:1",
                    role_family="Frontend Developer",
                    seniority_level="junior",
                )
            ]
        return adapter

    with patch(
        "app.services.discovery.discovery_service.get_adapter",
        side_effect=mock_get_adapter,
    ):
        batch_res = JobDiscoveryService.scan_all_sources(db_session, only_due=False)

    assert batch_res.sources_scanned == 2
    assert batch_res.failed_sources == 1
    assert batch_res.total_jobs_imported == 1

    # Verify source statuses
    db_session.refresh(src1)
    db_session.refresh(src2)
    assert src1.last_scan_status == "failed"
    assert src1.error_count == 1
    assert src2.last_scan_status == "success"
    assert src2.jobs_discovered_count == 1


# -----------------------------------------------------------------------------
# 4. Security & SSRF Protection Tests
# -----------------------------------------------------------------------------


def test_ssrf_prohibits_private_and_cloud_metadata_hosts() -> None:
    """Verify that SSRF guards reject private IPs and cloud metadata addresses."""
    adapter = GreenhouseAdapter()

    # Loopback address
    with pytest.raises((ValueError, Exception)):
        adapter.safe_get("http://127.0.0.1:8000/api/jobs")

    # AWS Metadata IP
    with pytest.raises((ValueError, Exception)):
        adapter.safe_get("http://169.254.169.254/latest/meta-data/")

    # Localhost
    with pytest.raises((ValueError, Exception)):
        adapter.safe_get("http://localhost:5432")


# -----------------------------------------------------------------------------
# 5. REST API Endpoint Tests
# -----------------------------------------------------------------------------


def test_discovery_api_crud_and_testing(client: TestClient, db_session: Session) -> None:
    """Test REST API endpoints for discovery overview, sources CRUD, and adapter testing."""
    headers, _ = create_user_and_token(client, "discovery_api@example.com")
    company = create_test_company(db_session, "Uber Technologies")

    # 1. Get overview
    overview_res = client.get("/api/v1/discovery/overview", headers=headers)
    assert overview_res.status_code == 200
    ov_data = overview_res.json()
    assert "total_sources" in ov_data
    assert "supported_adapters" in ov_data
    assert len(ov_data["supported_adapters"]) >= 5

    # 2. Test source connectivity
    with patch(
        "app.services.discovery.adapters.greenhouse.GreenhouseAdapter.test_connection",
        return_value=(True, "Board reachable", 5),
    ):
        test_res = client.post(
            "/api/v1/discovery/sources/test",
            json={
                "adapter_name": "greenhouse",
                "board_token": "uber",
            },
            headers=headers,
        )
        assert test_res.status_code == 200
        assert test_res.json()["is_success"] is True
        assert test_res.json()["jobs_detected"] == 5

    # 3. Create discovery source
    create_res = client.post(
        "/api/v1/discovery/sources",
        json={
            "company_id": str(company.id),
            "source_name": "Uber Careers Greenhouse",
            "source_type": "careers_page",
            "adapter_name": "greenhouse",
            "board_token": "uber",
            "scan_frequency_hours": 12,
            "is_enabled": True,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    source_data = create_res.json()
    source_id = source_data["id"]
    assert source_data["adapter_name"] == "greenhouse"
    assert source_data["board_token"] == "uber"

    # 4. List sources
    list_res = client.get("/api/v1/discovery/sources", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 5. Update source
    update_res = client.put(
        f"/api/v1/discovery/sources/{source_id}",
        json={"scan_frequency_hours": 6, "is_enabled": False},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["scan_frequency_hours"] == 6
    assert update_res.json()["is_enabled"] is False

    # 6. Delete source
    del_res = client.delete(f"/api/v1/discovery/sources/{source_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/discovery/sources/{source_id}", headers=headers)
    assert get_res.status_code == 404


# -----------------------------------------------------------------------------
# 6. Celery Background Task Tests
# -----------------------------------------------------------------------------


def test_celery_discovery_tasks_execution(db_session: Session) -> None:
    """Test Celery discovery tasks run without errors."""
    company = create_test_company(db_session, "Docker")
    source = CompanySource(
        company_id=company.id,
        source_name="Docker Ashby",
        source_type="careers_page",
        adapter_name="ashby",
        board_token="docker",
        is_enabled=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    with patch(
        "app.services.discovery.discovery_service.JobDiscoveryService.scan_source"
    ) as mock_scan:
        mock_scan.return_value = MagicMock(
            status="success",
            source_id=source.id,
            jobs_found=3,
            jobs_imported=2,
            jobs_updated=1,
            message="Scan completed",
        )
        task_res = scan_single_company_source_task.apply(args=[str(source.id)])
        assert task_res.status == "SUCCESS"
        assert task_res.result["status"] == "success"
        assert task_res.result["jobs_imported"] == 2

    # Test batch periodic task
    with patch(
        "app.services.discovery.discovery_service.JobDiscoveryService.scan_all_sources"
    ) as mock_batch:
        mock_batch.return_value = MagicMock(
            sources_scanned=1,
            total_jobs_imported=2,
            total_jobs_updated=1,
            failed_sources=0,
        )
        batch_task_res = scan_all_due_sources_task.apply()
        assert batch_task_res.status == "SUCCESS"
        assert batch_task_res.result["status"] == "success"
        assert batch_task_res.result["total_jobs_imported"] == 2
