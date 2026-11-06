import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


def create_user_and_token(
    client: TestClient,
    email: str = "applicant@example.com",
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Applicant User",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_test_entities(
    db: Session, user_email: str
) -> tuple[User, Company, Job, Resume, ResumeVersion]:
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=user_email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Applicant User",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="Nova Technologies",
        normalized_name="nova technologies",
        website_url="https://novatech.example",
        normalized_domain="novatech.example",
        category="product_company",
    )
    db.add(company)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Full Stack Engineer",
        normalized_title="full stack engineer",
        description="Looking for early career full stack developers.",
        skills_tags=["TypeScript", "React", "Python"],
        seniority_level="entry_level",
        work_arrangement="remote",
        job_url="https://novatech.example/jobs/101",
        verification_status="verified",
    )
    db.add(job)

    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Main Technical Resume",
    )
    db.add(resume)
    db.flush()

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="resume_v1.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path=f"storage/resumes/{user.id}/{resume.id}/v1/resume.pdf",
        parsing_status="parsed",
        parsed_content={"skills": ["Python", "TypeScript"]},
        raw_text="Full stack engineer with Python and TypeScript experience.",
    )
    db.add(version)
    resume.current_version_id = version.id
    db.commit()

    return user, company, job, resume, version


# --- Tests ---


def test_create_and_get_application(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_create@example.com")
    user, company, job, resume, version = setup_test_entities(db_session, email)

    payload = {
        "job_id": str(job.id),
        "company_id": str(company.id),
        "title": "Full Stack Engineer",
        "company_name": "Nova Technologies",
        "status": "interested",
        "application_channel": "official_portal",
        "application_url": "https://novatech.example/jobs/101",
        "resume_id": str(resume.id),
        "resume_version_id": str(version.id),
        "recruiter_name": "Sarah Recruiter",
        "recruiter_email": "sarah@novatech.example",
        "notes": "Met at virtual career fair.",
    }

    # 1. Create Application
    resp = client.post("/api/v1/applications", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    app_id = data["id"]
    assert data["title"] == "Full Stack Engineer"
    assert data["company_name"] == "Nova Technologies"
    assert data["status"] == "interested"
    assert data["submission_confirmed"] is False
    assert len(data["status_history"]) == 1
    assert data["status_history"][0]["to_status"] == "interested"
    assert len(data["activities"]) == 1

    # 2. Get Detail
    get_resp = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == app_id
    assert get_resp.json()["recruiter_name"] == "Sarah Recruiter"


def test_manual_application_creation(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_manual@example.com")
    setup_test_entities(db_session, email)

    # Standalone manual application with no pre-existing job or company record
    payload = {
        "title": "Junior Python Developer",
        "company_name": "Acme Labs",
        "status": "preparing",
        "application_channel": "email",
        "recruiter_email": "jobs@acmelabs.example",
        "notes": "Preparing tailored cover letter.",
    }

    resp = client.post("/api/v1/applications", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Junior Python Developer"
    assert data["company_name"] == "Acme Labs"
    assert data["job_id"] is None
    assert data["company_id"] is None
    assert data["status"] == "preparing"


def test_status_transitions_and_history(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_status@example.com")
    setup_test_entities(db_session, email)

    # 1. Create
    resp = client.post(
        "/api/v1/applications",
        json={"title": "Software Engineer", "company_name": "Corp", "status": "interested"},
        headers=headers,
    )
    app_id = resp.json()["id"]

    # 2. Transition to 'preparing'
    p1 = client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "preparing", "notes": "Drafting technical answers."},
        headers=headers,
    )
    assert p1.status_code == 200
    assert p1.json()["status"] == "preparing"

    # 3. Transition to 'applied' (Submission confirmed by user)
    p2 = client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={
            "status": "applied",
            "submission_confirmed": True,
            "notes": "Submitted via company careers portal.",
        },
        headers=headers,
    )
    assert p2.status_code == 200
    app_applied = p2.json()
    assert app_applied["status"] == "applied"
    assert app_applied["submission_confirmed"] is True
    assert app_applied["applied_at"] is not None

    # 4. Transition to 'interview'
    p3 = client.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "interview", "notes": "HR recruiter reached out for screen."},
        headers=headers,
    )
    assert p3.status_code == 200
    assert p3.json()["status"] == "interview"

    # 5. Verify full immutable history length
    detail = client.get(f"/api/v1/applications/{app_id}", headers=headers).json()
    history = detail["status_history"]
    assert len(history) == 4
    statuses = [h["to_status"] for h in history]
    assert "interested" in statuses
    assert "preparing" in statuses
    assert "applied" in statuses
    assert "interview" in statuses


def test_link_opened_does_not_falsely_submit(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_link@example.com")
    setup_test_entities(db_session, email)

    resp = client.post(
        "/api/v1/applications",
        json={
            "title": "Frontend Engineer",
            "company_name": "Web Co",
            "status": "interested",
            "application_url": "https://webco.example/apply",
        },
        headers=headers,
    )
    app_id = resp.json()["id"]

    # Record link opened
    link_resp = client.post(f"/api/v1/applications/{app_id}/link-opened", headers=headers)
    assert link_resp.status_code == 200
    updated = link_resp.json()
    assert updated["link_opened_at"] is not None
    # Crucial assertion: status must NOT become 'applied' simply because link was opened
    assert updated["status"] == "interested"
    assert updated["submission_confirmed"] is False


def test_activity_timeline_crud(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_act@example.com")
    setup_test_entities(db_session, email)

    app_id = client.post(
        "/api/v1/applications",
        json={"title": "DevOps Engineer", "company_name": "Cloud Infra"},
        headers=headers,
    ).json()["id"]

    # 1. Add Note Activity
    act_resp = client.post(
        f"/api/v1/applications/{app_id}/activities",
        json={
            "activity_type": "recruiter_communication",
            "title": "Spoke with recruiter on LinkedIn",
            "description": "Discussed team culture and remote work options.",
        },
        headers=headers,
    )
    assert act_resp.status_code == 201
    act_id = act_resp.json()["id"]
    assert act_resp.json()["activity_type"] == "recruiter_communication"

    # 2. Update Activity
    patch_act = client.patch(
        f"/api/v1/applications/{app_id}/activities/{act_id}",
        json={"title": "Phone Call with Talent Partner"},
        headers=headers,
    )
    assert patch_act.status_code == 200
    assert patch_act.json()["title"] == "Phone Call with Talent Partner"

    # 3. Delete Activity
    del_act = client.delete(f"/api/v1/applications/{app_id}/activities/{act_id}", headers=headers)
    assert del_act.status_code == 204


def test_interview_and_assessment_crud(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_interview@example.com")
    setup_test_entities(db_session, email)

    app_id = client.post(
        "/api/v1/applications",
        json={"title": "Backend Dev", "company_name": "Scale AI Systems"},
        headers=headers,
    ).json()["id"]

    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Schedule Technical Interview
    create_resp = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        json={
            "interview_type": "technical",
            "title": "System Architecture & Python Deep Dive",
            "round_number": 1,
            "scheduled_at": scheduled_time,
            "duration_minutes": 60,
            "meeting_url": "https://meet.example/interview-1",
            "interviewer_names": "Bob Lead Engineer",
            "preparation_notes": "Review async concurrency and SQLAlchemy indexing.",
            "status": "scheduled",
            "outcome": "pending",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    iv_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "scheduled"
    assert create_resp.json()["round_number"] == 1

    # 2. Update Interview Outcome to Completed
    patch_resp = client.patch(
        f"/api/v1/applications/{app_id}/interviews/{iv_id}",
        json={
            "status": "completed",
            "outcome": "passed",
            "feedback": "Strong architecture design solutions.",
            "next_steps": "Awaiting final round schedule.",
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"
    assert patch_resp.json()["outcome"] == "passed"

    # 3. Verify activity was logged in timeline
    app_detail = client.get(f"/api/v1/applications/{app_id}", headers=headers).json()
    timeline_types = [a["activity_type"] for a in app_detail["activities"]]
    assert "interview_scheduled" in timeline_types
    assert "interview_completed" in timeline_types

    # 4. Delete Interview
    del_resp = client.delete(f"/api/v1/applications/{app_id}/interviews/{iv_id}", headers=headers)
    assert del_resp.status_code == 204


def test_application_analytics_accuracy(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "test_analytics@example.com")
    setup_test_entities(db_session, email)

    now = datetime.now(timezone.utc)
    future_deadline = (now + timedelta(days=3)).isoformat()
    future_follow_up = (now + timedelta(days=5)).isoformat()

    # App 1: Interested with upcoming deadline
    client.post(
        "/api/v1/applications",
        json={
            "title": "Engineer 1",
            "company_name": "Company A",
            "status": "interested",
            "deadline_at": future_deadline,
        },
        headers=headers,
    )

    # App 2: Applied with upcoming follow up
    client.post(
        "/api/v1/applications",
        json={
            "title": "Engineer 2",
            "company_name": "Company B",
            "status": "applied",
            "submission_confirmed": True,
            "next_follow_up_at": future_follow_up,
        },
        headers=headers,
    )

    # App 3: Offer
    client.post(
        "/api/v1/applications",
        json={"title": "Engineer 3", "company_name": "Company C", "status": "offer"},
        headers=headers,
    )

    # App 4: Rejected
    client.post(
        "/api/v1/applications",
        json={"title": "Engineer 4", "company_name": "Company D", "status": "rejected"},
        headers=headers,
    )

    # Fetch Analytics
    analytics_resp = client.get("/api/v1/applications/analytics", headers=headers)
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()

    assert analytics["total_applications"] == 4
    assert analytics["in_progress_count"] == 2  # interested and applied
    assert analytics["offers_count"] == 1
    assert analytics["rejections_count"] == 1
    assert analytics["upcoming_deadlines_count"] == 1
    assert analytics["upcoming_follow_ups_count"] == 1
    assert analytics["status_distribution"]["offer"] == 1
    assert analytics["status_distribution"]["rejected"] == 1
    assert analytics["status_distribution"]["interested"] == 1
    assert analytics["status_distribution"]["applied"] == 1


def test_user_isolation(client: TestClient, db_session: Session) -> None:
    headers_a, email_a = create_user_and_token(client, "user_a_app@example.com")
    headers_b, email_b = create_user_and_token(client, "user_b_app@example.com")
    setup_test_entities(db_session, email_a)
    setup_test_entities(db_session, email_b)

    # User A creates application
    app_a = client.post(
        "/api/v1/applications",
        json={"title": "Private Role", "company_name": "Secret Corp"},
        headers=headers_a,
    ).json()
    app_a_id = app_a["id"]

    # User B cannot access User A's application
    get_b = client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B cannot update User A's application
    patch_b = client.patch(
        f"/api/v1/applications/{app_a_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert patch_b.status_code == 404

    # User B cannot delete User A's application
    del_b = client.delete(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert del_b.status_code == 404


def test_application_deletion_preserves_shared_entities(
    client: TestClient, db_session: Session
) -> None:
    headers, email = create_user_and_token(client, "test_cascade@example.com")
    user, company, job, resume, version = setup_test_entities(db_session, email)

    resp = client.post(
        "/api/v1/applications",
        json={
            "job_id": str(job.id),
            "company_id": str(company.id),
            "resume_id": str(resume.id),
            "resume_version_id": str(version.id),
            "title": "Engineer Role",
            "company_name": company.name,
        },
        headers=headers,
    )
    app_id = resp.json()["id"]

    # Delete application
    del_resp = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify Job, Company, and Resume still exist in DB
    db_session.expire_all()
    assert db_session.get(Job, job.id) is not None
    assert db_session.get(Company, company.id) is not None
    assert db_session.get(Resume, resume.id) is not None
