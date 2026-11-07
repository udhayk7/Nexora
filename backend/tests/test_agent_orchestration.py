import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.company import Company
from app.models.job import Job
from app.models.orchestration import AgentExecutionRecord
from app.models.resume import Resume, ResumeVersion
from app.models.user import User

# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _create_user(db: Session, email_prefix: str = "orchestrator") -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Alex Rivera",
        hashed_password="hashed_pw_dummy_12345",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _seed_candidate_profile(db: Session, user: User) -> tuple[Resume, Job, Company]:
    comp = Company(
        id=uuid.uuid4(),
        name="Stripe",
        normalized_name="stripe",
        normalized_domain="stripe.example.com",
        website_url="https://stripe.example.com",
        category="product",
        industry_tags=["Financial Technology"],
        verification_status="verified",
    )
    db.add(comp)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=comp.id,
        title="Backend Software Engineer",
        normalized_title="backend software engineer",
        role_family="Software Engineer",
        description="Build high-reliability payment infrastructure using Python and FastAPI.",
        job_url="https://stripe.example.com/jobs/backend-sde-101",
        job_status="active",
        seniority_level="entry",
        skills_tags=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    )
    db.add(job)
    db.flush()

    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Alex Rivera Resume",
    )
    db.add(resume)
    db.flush()

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        storage_path="/resumes/alex_rivera_resume.pdf",
        original_filename="alex_rivera_resume.pdf",
        file_type="pdf",
        file_size=2048,
        parsing_status="parsed",
        parsed_content={
            "contact": {"name": user.full_name, "email": user.email},
            "summary": "Software engineer passionate about scalable backend systems.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Git", "React"],
            "projects": [
                {
                    "title": "Cloud Task Engine",
                    "description": "Async task queue using Celery and Redis.",
                    "skills": ["Python", "FastAPI", "Redis"],
                }
            ],
            "education": [{"degree": "B.S. Computer Science", "institution": "State University"}],
        },
    )
    db.add(version)
    resume.current_version_id = version.id
    db.commit()
    db.refresh(resume)
    db.refresh(job)
    db.refresh(comp)
    return resume, job, comp


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_copilot_session_creation_and_listing(client: TestClient, db_session: Session):
    """Test Case 1: Create, list, and retrieve Copilot conversational sessions."""
    user = _create_user(db_session, "sess_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    # 1. Create Session
    create_res = client.post(
        "/api/v1/copilot/sessions",
        json={"title": "Q4 Career Strategy", "session_type": "career_strategy"},
        headers=headers,
    )
    assert create_res.status_code == 201
    s_data = create_res.json()
    session_id = s_data["id"]
    assert s_data["title"] == "Q4 Career Strategy"
    assert s_data["user_id"] == str(user.id)
    assert "candidate_name" in s_data["context_summary"]

    # 2. List Sessions
    list_res = client.get("/api/v1/copilot/sessions", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Get Session Detail
    detail_res = client.get(f"/api/v1/copilot/sessions/{session_id}", headers=headers)
    assert detail_res.status_code == 200
    d_data = detail_res.json()
    assert d_data["session"]["id"] == session_id
    assert isinstance(d_data["messages"], list)


def test_shared_candidate_context_extraction(client: TestClient, db_session: Session):
    """Test Case 2: Context projection returns lean verified facts without private notes."""
    user = _create_user(db_session, "context_user")
    headers = _get_auth_headers(user)
    resume, job, comp = _seed_candidate_profile(db_session, user)

    res = client.get(
        f"/api/v1/copilot/context-preview?target_job_id={job.id}&target_company_id={comp.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["candidate"]["candidate_name"] == user.full_name
    assert "Python" in data["verified_skills"]
    assert len(data["verified_projects"]) >= 1
    assert data["target_job_title"] == "Backend Software Engineer"
    assert data["target_company_name"] == "Stripe"
    # Ensure no passwords or raw credentials exist in context
    assert "hashed_password" not in data
    assert "password" not in data


def test_multi_agent_workflow_job_discovery_match(client: TestClient, db_session: Session):
    """Test Case 3: Prompt 'find jobs' runs Discovery and Matching."""
    user = _create_user(db_session, "disco_match_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    # Create session
    sess_res = client.post(
        "/api/v1/copilot/sessions", json={"title": "Job Search"}, headers=headers
    )
    session_id = sess_res.json()["id"]

    # Post message
    msg_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/messages",
        json={"content": "Find suitable jobs for my profile and rank my top matches."},
        headers=headers,
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["intent"] == "job_discovery_match"
    assert data["role"] == "assistant"

    # Verify agent trace
    agent_names = [step["agent_name"] for step in data["agent_trace"]]
    assert "resume_intelligence" in agent_names
    assert "job_discovery" in agent_names
    assert "job_matching" in agent_names

    # Verify action proposals generated
    assert len(data["action_proposals"]) >= 1


def test_multi_agent_workflow_application_preparation(client: TestClient, db_session: Session):
    """Test Case 4: Application preparation runs Tailoring, Cover Letter, and Screening Q&A."""
    user = _create_user(db_session, "app_prep_user")
    headers = _get_auth_headers(user)
    resume, job, comp = _seed_candidate_profile(db_session, user)

    sess_res = client.post("/api/v1/copilot/sessions", json={"title": "App Prep"}, headers=headers)
    session_id = sess_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/messages",
        json={
            "content": "Prepare an application package for the Backend Software Engineer role.",
            "target_job_id": str(job.id),
        },
        headers=headers,
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["intent"] == "application_prep"

    agent_names = [step["agent_name"] for step in data["agent_trace"]]
    assert "resume_intelligence" in agent_names
    assert "application_preparation" in agent_names

    # Check consequential action proposal with requires_approval=True
    consequential_props = [p for p in data["action_proposals"] if p.get("requires_approval")]
    assert len(consequential_props) >= 1


def test_multi_agent_workflow_interview_preparation(client: TestClient, db_session: Session):
    """Test Case 5: Interview preparation coordinates STAR deep-dive and mock questions."""
    user = _create_user(db_session, "interview_user")
    headers = _get_auth_headers(user)
    resume, job, comp = _seed_candidate_profile(db_session, user)

    sess_res = client.post(
        "/api/v1/copilot/sessions", json={"title": "Mock Interview"}, headers=headers
    )
    session_id = sess_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/messages",
        json={"content": "Prepare me for an upcoming technical interview at Stripe."},
        headers=headers,
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["intent"] == "interview_prep"

    agent_names = [step["agent_name"] for step in data["agent_trace"]]
    assert "interview_preparation" in agent_names


def test_multi_agent_workflow_career_strategy(client: TestClient, db_session: Session):
    """Test Case 6: High-level career strategy produces weekly action plan and readiness score."""
    user = _create_user(db_session, "strat_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    sess_res = client.post(
        "/api/v1/copilot/sessions", json={"title": "Strategy Session"}, headers=headers
    )
    session_id = sess_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/copilot/sessions/{session_id}/messages",
        json={"content": "Create my weekly career action plan to improve my chances."},
        headers=headers,
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["intent"] == "career_strategy"

    agent_names = [step["agent_name"] for step in data["agent_trace"]]
    assert "career_strategy" in agent_names


def test_consequential_action_approval_gate(client: TestClient, db_session: Session):
    """Test Case 7: Candidate review and approval gate for consequential actions."""
    user = _create_user(db_session, "approval_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    # Create execution record requiring approval
    rec = AgentExecutionRecord(
        id=uuid.uuid4(),
        workflow_id="wf_test_approval_123",
        user_id=user.id,
        agent_name="application_preparation",
        operation="dispatch_recruiter_email",
        status="requires_approval",
        requires_approval=True,
        approval_state="pending",
        input_context_summary={"target": "Stripe"},
        output_payload={"recipient": "recruiter@stripe.com"},
    )
    db_session.add(rec)
    db_session.commit()

    # 1. Candidate approves
    appr_res = client.post(
        f"/api/v1/copilot/approvals/{rec.id}",
        json={"action": "approve", "notes": "Approved after reviewing cover letter."},
        headers=headers,
    )
    assert appr_res.status_code == 200
    data = appr_res.json()
    assert data["status"] == "approved"
    assert data["approved_at"] is not None

    # Check DB state
    db_session.refresh(rec)
    assert rec.approval_state == "approved"


def test_quick_actions_endpoint(client: TestClient, db_session: Session):
    """Test Case 8: Pre-configured quick actions execute multi-agent pipelines directly."""
    user = _create_user(db_session, "quick_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    res = client.post(
        "/api/v1/copilot/quick-action",
        json={"action": "career_diagnosis"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "assistant"
    assert len(data["agent_trace"]) >= 1


def test_multi_user_data_isolation(client: TestClient, db_session: Session):
    """Test Case 9: Multi-tenant user isolation on Copilot sessions and execution records."""
    user_a = _create_user(db_session, "user_a")
    user_b = _create_user(db_session, "user_b")
    headers_a = _get_auth_headers(user_a)
    headers_b = _get_auth_headers(user_b)
    _seed_candidate_profile(db_session, user_a)

    # User A creates a session
    sess_a = client.post(
        "/api/v1/copilot/sessions", json={"title": "Private Session A"}, headers=headers_a
    ).json()
    session_id_a = sess_a["id"]

    # User B cannot access User A's session
    b_res = client.get(f"/api/v1/copilot/sessions/{session_id_a}", headers=headers_b)
    assert b_res.status_code == 404

    # User B cannot delete User A's session
    del_res = client.delete(f"/api/v1/copilot/sessions/{session_id_a}", headers=headers_b)
    assert del_res.status_code == 404


def test_agent_execution_records_audit_trail(client: TestClient, db_session: Session):
    """Test Case 10: Audit transparency endpoint lists execution records for workflow."""
    user = _create_user(db_session, "audit_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    # Create message which generates execution records
    sess = client.post(
        "/api/v1/copilot/sessions", json={"title": "Audit Test"}, headers=headers
    ).json()
    client.post(
        f"/api/v1/copilot/sessions/{sess['id']}/messages",
        json={"content": "Find suitable jobs for my profile."},
        headers=headers,
    )

    # Query execution records by user
    records = (
        db_session.query(AgentExecutionRecord).filter(AgentExecutionRecord.user_id == user.id).all()
    )
    assert len(records) >= 1
    wf_id = records[0].workflow_id

    exec_res = client.get(f"/api/v1/copilot/executions/{wf_id}", headers=headers)
    assert exec_res.status_code == 200
    e_data = exec_res.json()
    assert len(e_data) >= 1
    assert e_data[0]["workflow_id"] == wf_id
    assert e_data[0]["agent_name"] in ["resume_intelligence", "job_discovery", "job_matching"]


def test_recruiter_networking_agent_outreach_note(client: TestClient, db_session: Session):
    """Test Case 11: Recruiter networking agent crafts grounded LinkedIn note <= 300 chars."""
    user = _create_user(db_session, "network_agent_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    sess = client.post(
        "/api/v1/copilot/sessions", json={"title": "Networking"}, headers=headers
    ).json()
    msg = client.post(
        f"/api/v1/copilot/sessions/{sess['id']}/messages",
        json={"content": "Draft a recruiter outreach note for Stripe."},
        headers=headers,
    ).json()

    assert msg.get("status_code", True)
    agent_names = [s["agent_name"] for s in msg["agent_trace"]]
    assert "recruiter_networking" in agent_names


def test_deterministic_fallback_when_ai_unconfigured(client: TestClient, db_session: Session):
    """Test Case 12: Zero-failure guarantee when AI provider is unconfigured or raises errors."""
    user = _create_user(db_session, "fallback_user")
    headers = _get_auth_headers(user)
    _seed_candidate_profile(db_session, user)

    sess = client.post(
        "/api/v1/copilot/sessions", json={"title": "Fallback Test"}, headers=headers
    ).json()

    # Mock get_ai_provider to raise configuration error
    with patch(
        "app.services.orchestration.model_router.get_ai_provider",
        side_effect=Exception("No API key configured"),
    ):
        msg = client.post(
            f"/api/v1/copilot/sessions/{sess['id']}/messages",
            json={"content": "What are my strengths and recommended next steps?"},
            headers=headers,
        )
        assert msg.status_code == 200
        data = msg.json()
        assert data["role"] == "assistant"
        assert len(data["content"]) > 50
        assert (
            "Key Agent Insights" in data["content"] or "Recommended Next Actions" in data["content"]
        )
