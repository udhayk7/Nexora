import io
import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.analysis import ResumeAnalysis
from app.models.company import Company
from app.models.job import Job
from app.models.networking import RecruiterProfile
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


def _create_user(db: Session, email: str, name: str) -> tuple[User, dict[str, str]]:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("SecurePassword123!"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    token = create_access_token(subject=str(user.id))
    return user, {"Authorization": f"Bearer {token}"}


def _mock_analysis_result() -> dict[str, Any]:
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


def _seed_user_resume(db: Session, user: User) -> tuple[Resume, ResumeVersion]:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title=f"{user.full_name} Resume",
    )
    db.add(resume)
    db.flush()

    ver = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="resume.pdf",
        storage_path=f"{user.id}/{resume.id}/resume.pdf",
        file_type="pdf",
        file_size=2048,
        parsing_status="parsed",
        parsed_content={
            "contact": {"name": user.full_name, "email": user.email, "links": []},
            "summary": "Software Engineer experienced in backend APIs.",
            "skills": ["python", "fastapi", "postgresql", "redis", "algorithms"],
            "experience": [],
            "education": [],
            "projects": ["Built real-time task manager"],
            "certifications": [],
        },
    )
    db.add(ver)
    resume.current_version_id = ver.id
    db.flush()

    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=ver.id,
        status="completed",
        provider="deterministic",
        model="v1.0",
        result=_mock_analysis_result(),
    )
    db.add(analysis)
    db.commit()
    return resume, ver


def test_workflow_a_candidate_onboarding(client: TestClient, db_session: Session) -> None:
    """Workflow A: Registration -> Login -> Upload Resume -> Extract Profile -> Set Preferences."""
    email = f"candidate_{uuid.uuid4().hex[:6]}@example.com"

    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!", "full_name": "Dev Candidate"},
    )
    assert reg_res.status_code == 201

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3. Upload Resume (Mock PDF)
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Dev Candidate) >>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"title": "Dev Candidate Primary Resume"},
        headers=auth_headers,
    )
    assert upload_res.status_code == 201
    resume_data = upload_res.json()
    assert resume_data["title"] == "Dev Candidate Primary Resume"

    # 4. Extract & Review Profile
    me_res = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 5. Configure Career Preferences
    pref_res = client.put(
        "/api/v1/matches/preferences",
        json={
            "target_role_families": ["backend_engineer", "fullstack_engineer"],
            "preferred_locations": ["Remote", "Bengaluru"],
            "min_salary": 1800000,
        },
        headers=auth_headers,
    )
    assert pref_res.status_code == 200
    assert "backend_engineer" in pref_res.json()["target_role_families"]


def test_workflow_b_job_discovery_and_matching(client: TestClient, db_session: Session) -> None:
    """Workflow B: Ingestion -> Normalization -> Deduplication -> Match scoring.

    Verifies recommendations.
    """
    user, headers = _create_user(db_session, "job_hunter@example.com", "Job Hunter")
    _seed_user_resume(db_session, user)

    # Create company and job
    company = Company(
        id=uuid.uuid4(),
        name="Apex Cloud Systems",
        normalized_name="apex cloud systems",
        website_url="https://apexcloud.example",
        normalized_domain="apexcloud.example",
        category="product_company",
    )
    db_session.add(company)
    db_session.flush()

    job1 = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Junior Python Engineer",
        normalized_title="junior python engineer",
        role_family="backend_engineer",
        location_text="Bengaluru, Karnataka, India",
        work_arrangement="remote",
        job_url="https://apexcloud.example/careers/101",
        description="Join our team building FastAPI backends with PostgreSQL and Redis.",
        skills_tags=["python", "fastapi", "postgresql", "redis"],
        salary_min=1500000,
        salary_max=2000000,
        verification_status="verified",
    )
    db_session.add(job1)
    db_session.commit()

    # 1. Query Discovery
    jobs_res = client.get("/api/v1/jobs", headers=headers)
    assert jobs_res.status_code == 200
    job_items = jobs_res.json()["items"]
    assert any(j["title"] == "Junior Python Engineer" for j in job_items)

    # 2. Run Deterministic Job Matching
    match_res = client.post("/api/v1/matches/run", headers=headers)
    assert match_res.status_code == 200

    # 3. Retrieve Matches & Recommendations
    rec_res = client.get("/api/v1/recommendations", headers=headers)
    assert rec_res.status_code == 200
    assert "items" in rec_res.json()


def test_workflow_c_application_preparation(client: TestClient, db_session: Session) -> None:
    """Workflow C: Select Job -> Tailor Resume -> Generate Cover Letter -> Screening Q&A."""
    user, headers = _create_user(db_session, "tailor_user@example.com", "Tailor User")
    resume, ver = _seed_user_resume(db_session, user)

    company = Company(
        id=uuid.uuid4(),
        name="Nova AI",
        normalized_name="nova ai",
        website_url="https://novaai.example",
        normalized_domain="novaai.example",
    )
    db_session.add(company)
    db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Full Stack Engineer",
        normalized_title="full stack engineer",
        role_family="fullstack_engineer",
        location_text="Remote",
        job_url="https://novaai.example/jobs/99",
        description="We are hiring a Full Stack Engineer proficient with React and FastAPI.",
        skills_tags=["react", "fastapi", "python"],
        verification_status="verified",
    )
    db_session.add(job)
    db_session.commit()

    # 1. Start preparation via unified workflow
    prep_res = client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id), "resume_id": str(resume.id)},
        headers=headers,
    )
    assert prep_res.status_code == 200
    prep_data = prep_res.json()
    assert prep_data["job_id"] == str(job.id)

    # 2. Verify Assistant Cover Letter & Screening Q&A items exist
    assert "cover_letter" in prep_data
    assert "qa_prep" in prep_data
    assert len(prep_data["qa_prep"]) > 0


def test_workflow_d_application_execution(client: TestClient, db_session: Session) -> None:
    """Workflow D: Approve Preparation -> Execution Channel -> Confirmation Safety."""
    user, headers = _create_user(db_session, "executor@example.com", "Executor User")
    resume, ver = _seed_user_resume(db_session, user)

    company = Company(
        id=uuid.uuid4(),
        name="Stripe Systems",
        normalized_name="stripe systems",
        website_url="https://stripe.example",
        normalized_domain="stripe.example",
    )
    db_session.add(company)
    db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Software Engineer II",
        normalized_title="software engineer ii",
        role_family="backend_engineer",
        location_text="Remote",
        job_url="https://stripe.example/jobs/42",
        description="Backend systems engineering.",
        skills_tags=["python", "distributed_systems"],
        verification_status="verified",
    )
    db_session.add(job)
    db_session.commit()

    # Initialize preparation record first
    client.post(
        "/api/v1/career-workflow/preparation/start",
        json={"job_id": str(job.id), "resume_id": str(resume.id)},
        headers=headers,
    )

    # 1. Candidate explicitly approves preparation for official portal channel
    approve_res = client.post(
        f"/api/v1/career-workflow/preparation/{job.id}/approve",
        json={"channel": "official_portal", "notes": "Approved for submission via Workday"},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["execution_status"] == "ready_to_apply"

    # 2. Portal opening action succeeds
    portal_res = client.post(
        f"/api/v1/career-workflow/execution/portal-open/{job.id}",
        headers=headers,
    )
    assert portal_res.status_code == 200
    assert portal_res.json()["portal_url"] == job.job_url

    # 3. Confirm submission updates application status to "applied"
    confirm_res = client.post(
        f"/api/v1/career-workflow/execution/portal-confirm/{job.id}",
        json={"confirmation_notes": "Application submitted, ref #12345"},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "success"
    assert confirm_res.json()["execution_status"] == "submitted_and_confirmed"


def test_workflow_e_networking(client: TestClient, db_session: Session) -> None:
    """Workflow E: Recruiter Discovery -> Match -> Save Contact -> Outreach -> Follow-up."""
    user, headers = _create_user(db_session, "networker@example.com", "Networker")

    recruiter = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Emily Recruiter",
        normalized_name="emily recruiter",
        company_name="Microsoft",
        designation="Senior Technical Recruiter",
        source_type="official_careers_page",
        verification_status="verified",
    )
    db_session.add(recruiter)
    db_session.commit()

    # 1. Discover Recruiters
    disc_res = client.get("/api/v1/networking/recruiters", headers=headers)
    assert disc_res.status_code == 200
    assert disc_res.json()["total"] >= 1

    # 2. Save Contact to CRM
    save_res = client.post(
        "/api/v1/networking/crm/contacts",
        json={"recruiter_id": str(recruiter.id), "networking_notes": "Connected via campus drive"},
        headers=headers,
    )
    assert save_res.status_code == 201
    contact_id = save_res.json()["id"]

    # 3. Generate Outreach Message (LinkedIn connection note strictly <= 300 chars)
    msg_res = client.post(
        "/api/v1/networking/outreach/generate",
        json={
            "recruiter_id": str(recruiter.id),
            "message_type": "linkedin_connection",
            "tone": "professional",
        },
        headers=headers,
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["character_count"] <= 300
    assert len(msg_data["body"]) <= 300

    # 4. Update follow-up status in CRM
    patch_res = client.patch(
        f"/api/v1/networking/crm/contacts/{contact_id}",
        json={"relationship_status": "contacted", "communication_channel": "linkedin"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["relationship_status"] == "contacted"


def test_workflow_f_interview_preparation(client: TestClient, db_session: Session) -> None:
    """Workflow F: Create Prep Plan -> Mock Interview Questions -> Evaluation."""
    user, headers = _create_user(db_session, "interviewee@example.com", "Interviewee")
    _seed_user_resume(db_session, user)

    company = Company(
        id=uuid.uuid4(),
        name="Oracle Cloud",
        normalized_name="oracle cloud",
        website_url="https://oracle.example",
        normalized_domain="oracle.example",
    )
    db_session.add(company)
    db_session.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Backend SDE",
        normalized_title="backend sde",
        role_family="backend_engineer",
        location_text="Remote",
        job_url="https://oracle.example/jobs/5",
        description="Core database and storage backend systems.",
        skills_tags=["python", "sql", "algorithms"],
        verification_status="verified",
    )
    db_session.add(job)
    db_session.commit()

    # 1. Start Interview Preparation Session
    start_res = client.post(
        "/api/v1/interview-prep/sessions",
        json={"job_id": str(job.id), "target_role": "Backend SDE"},
        headers=headers,
    )
    assert start_res.status_code == 201
    session_data = start_res.json()
    session_id = session_data["id"]
    questions = session_data["questions"]
    assert len(questions) > 0
    first_q_id = questions[0]["id"]

    # 2. Fetch Session Details
    q_res = client.get(f"/api/v1/interview-prep/sessions/{session_id}", headers=headers)
    assert q_res.status_code == 200
    assert len(q_res.json()["questions"]) > 0

    # 3. Submit Evaluation
    eval_res = client.post(
        f"/api/v1/interview-prep/sessions/{session_id}/questions/{first_q_id}/answer",
        json={
            "answer_text": (
                "I index columns on foreign keys and use composite indexes for compound filters."
            ),
            "time_spent_seconds": 30,
        },
        headers=headers,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["evaluation"] is not None
    assert "overall_score" in eval_data["evaluation"]
    assert 0 <= eval_data["evaluation"]["overall_score"] <= 100


def test_workflow_g_learning_and_portfolio(client: TestClient, db_session: Session) -> None:
    """Workflow G: Skill Roadmap -> Project Import -> Portfolio Studio -> Publish & Revoke."""
    user, headers = _create_user(db_session, "creator@example.com", "Creator")

    # 1. Generate Learning Roadmap
    rm_res = client.post(
        "/api/v1/learning-roadmaps",
        json={
            "track_key": "backend_python",
            "target_role": "Python Backend Engineer",
        },
        headers=headers,
    )
    assert rm_res.status_code == 201
    roadmap_id = rm_res.json()["id"]

    # 2. Get Roadmap details & projects
    detail_res = client.get(f"/api/v1/learning-roadmaps/{roadmap_id}", headers=headers)
    assert detail_res.status_code == 200
    milestones = detail_res.json()["milestones"]
    assert len(milestones) > 0

    # 3. Add Project to Portfolio Studio
    proj_res = client.post(
        "/api/v1/portfolios/projects",
        json={
            "title": "Distributed Task Scheduler",
            "problem_statement": "Prevent thundering herds with atomic Redis locks.",
            "description": "Implemented rate-limiting and Crawl-delay pacing.",
            "tech_stack": ["Python", "Redis", "Celery"],
            "repository_url": "https://github.com/creator/task-scheduler",
            "is_visible": True,
        },
        headers=headers,
    )
    assert proj_res.status_code == 201
    assert proj_res.json()["id"] is not None

    # 4. Preview Portfolio
    me_port = client.get("/api/v1/portfolios/me", headers=headers)
    assert me_port.status_code == 200
    slug = me_port.json()["public_slug"]

    # 5. Export PDF
    pdf_res = client.get("/api/v1/portfolios/export/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["Content-Type"] == "application/pdf"

    # 6. Publish Portfolio
    pub_res = client.post("/api/v1/portfolios/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # 7. Public access succeeds
    public_res = client.get(f"/api/v1/portfolios/public/{slug}")
    assert public_res.status_code == 200

    # 8. Unpublish and revoke public access
    unpub_res = client.post("/api/v1/portfolios/unpublish", headers=headers)
    assert unpub_res.status_code == 200

    # 9. Public access returns 404
    public_revoked = client.get(f"/api/v1/portfolios/public/{slug}")
    assert public_revoked.status_code == 404


def test_workflow_h_ai_career_copilot(client: TestClient, db_session: Session) -> None:
    """Workflow H: Create Session -> Career Query -> Multi-Agent Dispatch -> Context Retrieval."""
    user, headers = _create_user(db_session, "copilot_user@example.com", "Copilot User")

    # 1. Create Copilot Session
    sess_res = client.post(
        "/api/v1/copilot/sessions",
        json={"title": "Career Acceleration Session", "session_type": "career_strategy"},
        headers=headers,
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # 2. Post inquiry to Copilot
    msg_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/messages",
        json={"content": "What are my next career milestones for backend engineering?"},
        headers=headers,
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert "content" in msg_data
    assert "agent_trace" in msg_data

    # 3. Inspect shared context projection
    ctx_res = client.get("/api/v1/copilot/context-preview", headers=headers)
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()
    assert "target_roles" in ctx_data
    assert "career_readiness_score" in ctx_data
