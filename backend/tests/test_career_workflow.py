import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.application import JobApplication
from app.models.assistant import ApplicationEmail, ApplicationPreparation, CoverLetter
from app.models.company import Company
from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.models.workflow import CareerWorkflowRun


def _create_user(db: Session, prefix: str = "wf_user") -> User:
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"{prefix}_{unique_id}@example.com",
        hashed_password=hash_password("WorkflowPass123!"),
        full_name=f"{prefix.title()} Candidate",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _create_resume_with_parsed_data(db: Session, user: User) -> tuple[Resume, ResumeVersion]:
    res = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Master Python Backend Resume",
    )
    db.add(res)
    db.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=res.id,
        version_number=1,
        original_filename="master_resume.pdf",
        file_type="pdf",
        file_size=20480,
        storage_path="/tmp/fake_master.pdf",
        parsing_status="parsed",
        parsed_content={
            "contact": {
                "name": user.full_name,
                "email": user.email,
                "phone": "+1-555-0199",
                "location": "Bengaluru, India",
                "links": ["https://linkedin.com/in/testuser", "https://github.com/testuser"],
            },
            "summary": (
                "Junior Software Engineer specializing in Python, FastAPI, "
                "and PostgreSQL architectures."
            ),
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Git", "REST APIs"],
            "experience": [
                {
                    "title": "Backend Engineering Intern",
                    "company": "CloudTech Labs",
                    "date_range": "2025 - Present",
                    "bullets": [
                        "Architected scalable microservices using FastAPI and async PostgreSQL.",
                        "Implemented distributed caching with Redis.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech in Computer Science",
                    "institution": "National Institute of Technology",
                    "year": "2025",
                    "details": ["GPA 8.8/10"],
                }
            ],
        },
    )
    db.add(ver)
    res.current_version_id = ver.id
    db.commit()
    db.refresh(res)
    db.refresh(ver)
    return res, ver


def _create_company_and_job(
    db: Session,
    title: str = "Junior Backend Engineer",
    company_tier: str = "product",
    experience_level: str = "entry",
    is_active: bool = True,
    status_str: str = "active",
) -> tuple[Company, Job]:
    comp_name = f"Acme Systems {uuid.uuid4().hex[:6]}"
    comp = Company(
        id=uuid.uuid4(),
        name=comp_name,
        normalized_name=comp_name.lower().strip(),
        category=company_tier,
        website_url="https://acme.example.com",
    )
    db.add(comp)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=comp.id,
        title=title,
        normalized_title=title.lower().strip(),
        description=(
            "We are seeking an entry-level Python engineer with FastAPI and SQL experience."
        ),
        location_text="Bengaluru, India",
        work_arrangement="hybrid",
        seniority_level=experience_level,
        skills_tags=["Python", "FastAPI", "PostgreSQL"],
        job_status=status_str,
        verification_status="verified",
        job_url="https://acme.example.com/careers/backend-junior",
        application_url="https://acme.example.com/careers/backend-junior",
    )
    db.add(job)
    db.commit()
    db.refresh(comp)
    db.refresh(job)
    return comp, job


# =============================================================================
# 1. Integration Tests
# =============================================================================


def test_resume_upload_through_candidate_profile_creation(client: TestClient, db_session: Session):
    """Test Case 1: Start onboarding workflow from resume to candidate profile creation."""
    user = _create_user(db_session, "onboard_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)

    res = client.post(
        "/api/v1/career-workflow/onboarding/start",
        json={"resume_id": str(resume.id)},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "candidate_summary" in data
    assert data["candidate_summary"]["name"] == user.full_name
    assert "Python" in data["extracted_skills"]
    assert "Backend Developer" in data["extracted_roles"]

    # Verify UserMatchingPreference was populated
    pref = db_session.query(UserMatchingPreference).filter_by(user_id=user.id).first()
    assert pref is not None
    assert "Backend Developer" in pref.target_role_families
    assert "Bengaluru, India" in pref.preferred_locations

    # Verify WorkflowRun was recorded
    run = (
        db_session.query(CareerWorkflowRun)
        .filter_by(user_id=user.id, workflow_type="onboarding")
        .first()
    )
    assert run is not None
    assert run.status == "completed"
    assert run.progress_pct == 100


def test_candidate_profile_through_job_recommendations(client: TestClient, db_session: Session):
    """Test Case 2: Candidate profile review and discovery of matched opportunities."""
    user = _create_user(db_session, "recom_user")
    headers = _get_auth_headers(user)
    _create_resume_with_parsed_data(db_session, user)
    _create_company_and_job(db_session, title="Junior Python Developer", experience_level="entry")

    # Confirm candidate preferences
    confirm_payload = {
        "target_roles": ["Backend Developer", "Software Engineer"],
        "technical_skills": ["Python", "FastAPI", "SQL"],
        "preferred_locations": ["Bengaluru, India"],
        "work_arrangement_preferences": ["hybrid", "remote"],
        "min_salary": 500000.0,
        "salary_currency": "INR",
        "seniority": "entry",
    }
    confirm_res = client.post(
        "/api/v1/career-workflow/onboarding/confirm",
        json=confirm_payload,
        headers=headers,
    )
    assert confirm_res.status_code == 200

    # Query unified discovery
    disc_res = client.get(
        "/api/v1/career-workflow/discovery?filter_entry_level=true",
        headers=headers,
    )
    assert disc_res.status_code == 200
    disc_data = disc_res.json()
    assert disc_data["total_active_jobs"] >= 1
    assert disc_data["entry_level_count"] >= 1
    assert len(disc_data["opportunities"]) >= 1
    first_opp = disc_data["opportunities"][0]
    assert first_opp["is_entry_level"] is True
    assert first_opp["verification_status"] == "verified"


def test_job_recommendation_through_application_preparation(
    client: TestClient, db_session: Session
):
    """Test Case 3: Initializing unified application preparation workspace for target job."""
    user = _create_user(db_session, "prep_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Entry SDE Python")

    res = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )
    assert res.status_code == 200
    prep_data = res.json()
    assert prep_data["job_id"] == str(job.id)
    assert prep_data["job_title"] == job.title
    assert prep_data["company_name"] == comp.name
    assert prep_data["execution_status"] in ("not_started", "awaiting_approval")
    assert prep_data["portal_url"] == job.application_url

    # Check that GET endpoint returns identical state
    get_res = client.get(f"/api/v1/career-workflow/preparation/{job.id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["preparation_id"] == prep_data["preparation_id"]


def test_tailored_resume_generation(client: TestClient, db_session: Session):
    """Test Case 4: Verifying tailored resume association with preparation workspace."""
    user = _create_user(db_session, "tailor_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Python SDE 1")

    # Start preparation
    prep_res = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )
    assert prep_res.status_code == 200
    prep_data = prep_res.json()
    assert prep_data["tailored_resume"] is not None
    assert prep_data["tailored_resume"]["version_id"] == str(version.id)


def test_cover_letter_and_email_preparation(client: TestClient, db_session: Session):
    """Test Case 5: Verified cover letter and recruiter email components in preparation."""
    user = _create_user(db_session, "assets_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Cloud Backend Dev")

    # Mock cover letter & email creation in db
    prep_rec = ApplicationPreparation(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        resume_version_id=version.id,
        execution_status="awaiting_approval",
    )
    db_session.add(prep_rec)
    db_session.flush()

    cl = CoverLetter(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        preparation_id=prep_rec.id,
        version_number=1,
        content="Dear Hiring Manager at Acme, I am excited to apply...",
        is_approved=False,
    )
    db_session.add(cl)

    email = ApplicationEmail(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        preparation_id=prep_rec.id,
        email_type="application",
        subject=f"Application: {job.title} - {user.full_name}",
        body="Hi Recruiter, please find my resume attached.",
        recipient_email="recruiter@acme.example.com",
        status="draft",
    )
    db_session.add(email)
    db_session.commit()

    # Query workspace
    res = client.get(f"/api/v1/career-workflow/preparation/{job.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["cover_letter"] is not None
    assert data["cover_letter"]["id"] == str(cl.id)
    assert data["recruiter_email"] is not None
    assert data["recruiter_email"]["id"] == str(email.id)


def test_approval_and_email_execution(client: TestClient, db_session: Session):
    """Test Case 6: Approval gate followed by Gmail execution."""
    user = _create_user(db_session, "email_exec_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Associate Python Engineer")

    # Start preparation
    client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )

    # Approve preparation
    approve_res = client.post(
        f"/api/v1/career-workflow/preparation/{job.id}/approve",
        json={"channel": "gmail", "notes": "Approved for email application"},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["execution_status"] == "ready_to_apply"

    # Create dummy email
    email_id = uuid.uuid4()
    with patch("app.services.assistant_service.AssistantService.send_email_message") as mock_send:
        mock_send.return_value = MagicMock()

        exec_res = client.post(
            f"/api/v1/career-workflow/execution/gmail-send/{job.id}",
            json={"email_id": str(email_id), "confirm_send": True},
            headers=headers,
        )
        assert exec_res.status_code == 200
        assert exec_res.json()["execution_status"] == "submitted_and_confirmed"
        mock_send.assert_called_once()


def test_application_status_updates(client: TestClient, db_session: Session):
    """Test Case 7: Application status transitions correctly through execution lifecycle."""
    user = _create_user(db_session, "status_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="SDE Trainee")

    # Start prep
    client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )

    # Check initial preparation state
    prep = (
        db_session.query(ApplicationPreparation).filter_by(user_id=user.id, job_id=job.id).first()
    )
    assert prep is not None
    assert prep.execution_status in ("not_started", "awaiting_approval")

    # Approve
    client.post(
        f"/api/v1/career-workflow/preparation/{job.id}/approve",
        json={"channel": "official_portal"},
        headers=headers,
    )
    db_session.refresh(prep)
    assert prep.execution_status == "ready_to_apply"

    # Open Portal (strictly does not submit)
    open_res = client.post(
        f"/api/v1/career-workflow/execution/portal-open/{job.id}",
        headers=headers,
    )
    assert open_res.status_code == 200
    assert open_res.json()["execution_status"] == "application_page_opened"

    # Confirm Submission
    confirm_res = client.post(
        f"/api/v1/career-workflow/execution/portal-confirm/{job.id}",
        json={"confirmation_notes": "Submitted via Workday application portal."},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["execution_status"] == "submitted_and_confirmed"

    # Verify linked JobApplication status updated to 'applied'
    app = db_session.query(JobApplication).filter_by(user_id=user.id, job_id=job.id).first()
    assert app is not None
    assert app.status == "applied"


def test_duplicate_prevention_and_idempotency(client: TestClient, db_session: Session):
    """Test Case 8: Duplicate preparation calls return the existing record idempotently."""
    user = _create_user(db_session, "idemp_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Python API Developer")

    res1 = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )
    res2 = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["preparation_id"] == res2.json()["preparation_id"]

    # Verify only 1 ApplicationPreparation row exists in database
    count = (
        db_session.query(ApplicationPreparation).filter_by(user_id=user.id, job_id=job.id).count()
    )
    assert count == 1


def test_workflow_retries_and_failures(client: TestClient, db_session: Session):
    """Test Case 9: Workflow cancellation and invalid state rejection."""
    user = _create_user(db_session, "retry_user")
    headers = _get_auth_headers(user)

    # Create a pending workflow run
    run = CareerWorkflowRun(
        user_id=user.id,
        workflow_type="application_preparation",
        status="pending",
        current_step="initialized",
        progress_pct=10,
        retry_count=0,
        max_retries=3,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # Cancel workflow run
    cancel_res = client.post(
        f"/api/v1/career-workflow/runs/{run.id}/cancel",
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Second cancel attempt should be rejected with 400
    fail_res = client.post(
        f"/api/v1/career-workflow/runs/{run.id}/cancel",
        headers=headers,
    )
    assert fail_res.status_code == 400


def test_multi_user_data_isolation(client: TestClient, db_session: Session):
    """Test Case 10: Strict tenant isolation across candidates."""
    user_a = _create_user(db_session, "user_a")
    user_b = _create_user(db_session, "user_b")
    headers_a = _get_auth_headers(user_a)
    headers_b = _get_auth_headers(user_b)

    resume_a, ver_a = _create_resume_with_parsed_data(db_session, user_a)
    comp, job = _create_company_and_job(db_session, title="Isolated Python Dev")

    # User A starts preparation
    client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers_a,
    )

    # User B should NOT see User A's preparation
    prep_b = (
        db_session.query(ApplicationPreparation).filter_by(user_id=user_b.id, job_id=job.id).first()
    )
    assert prep_b is None

    # User A has workflow dashboard with 1 prep, User B has 0
    dash_a = client.get("/api/v1/career-workflow/dashboard", headers=headers_a).json()
    dash_b = client.get("/api/v1/career-workflow/dashboard", headers=headers_b).json()

    assert dash_a["incomplete_preparations_count"] >= 1
    assert dash_b["incomplete_preparations_count"] == 0


def test_expired_and_suspicious_job_handling(client: TestClient, db_session: Session):
    """Test Case 11: System halts application preparation for closed or expired jobs."""
    user = _create_user(db_session, "expired_user")
    headers = _get_auth_headers(user)
    _create_resume_with_parsed_data(db_session, user)

    # Closed job
    comp, closed_job = _create_company_and_job(
        db_session,
        title="Closed Python SDE",
        is_active=False,
        status_str="closed",
    )

    # Attempt to start preparation should fail with 400
    prep_res = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(closed_job.id)},
        headers=headers,
    )
    assert prep_res.status_code == 400
    res_json = prep_res.json()
    err_msg = res_json.get("detail") or res_json.get("error", {}).get("message", "")
    assert "closed" in err_msg.lower()


def test_confirmation_of_actual_application_submission(client: TestClient, db_session: Session):
    """Test Case 12: Distinct verification between portal open and candidate confirmed."""
    user = _create_user(db_session, "confirm_sub_user")
    headers = _get_auth_headers(user)
    resume, version = _create_resume_with_parsed_data(db_session, user)
    comp, job = _create_company_and_job(db_session, title="Verified Software Engineer")

    # Start preparation & approve
    client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id)},
        headers=headers,
    )
    client.post(
        f"/api/v1/career-workflow/preparation/{job.id}/approve",
        json={"channel": "official_portal"},
        headers=headers,
    )

    # Open portal: state is 'application_page_opened', application is NOT 'applied'
    open_res = client.post(
        f"/api/v1/career-workflow/execution/portal-open/{job.id}",
        headers=headers,
    )
    assert open_res.status_code == 200
    app = db_session.query(JobApplication).filter_by(user_id=user.id, job_id=job.id).first()
    assert app is not None
    assert app.status != "applied"

    # Confirm submission: state is 'submitted_and_confirmed', application is 'applied'
    confirm_res = client.post(
        f"/api/v1/career-workflow/execution/portal-confirm/{job.id}",
        json={"confirmation_notes": "Application submitted via company portal."},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    db_session.refresh(app)
    assert app.status == "applied"
