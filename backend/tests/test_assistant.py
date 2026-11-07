import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequestError
from app.core.oauth_state import generate_oauth_state, verify_oauth_state
from app.core.security import hash_password
from app.core.token_encryption import decrypt_token, encrypt_token
from app.models.analysis import ResumeAnalysis
from app.models.assistant import (
    GmailConnection,
)
from app.models.company import Company
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.services.gmail_service import GmailService

# ============================================================================
# Fixtures & Helpers
# ============================================================================


def create_user_and_auth(
    client: TestClient, email: str = "assistant_user@example.com"
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Assistant Candidate",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_assistant_entities(
    db: Session, user_email: str
) -> tuple[User, Company, Job, Resume, ResumeVersion]:
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=user_email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Assistant Candidate",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="TechCorp Dynamics",
        normalized_name="techcorp dynamics",
        website_url="https://techcorp.example.com",
        normalized_domain="techcorp.example.com",
        category="product_company",
    )
    db.add(company)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Software Engineer - Backend",
        normalized_title="software engineer - backend",
        description=(
            "We are seeking a Python / FastAPI engineer with SQL, Redis, and Celery experience."
        ),
        skills_tags=["Python", "FastAPI", "PostgreSQL", "Redis"],
        seniority_level="entry_level",
        work_arrangement="hybrid",
        job_url="https://techcorp.example.com/careers/apply/123",
        application_url="https://techcorp.example.com/careers/apply/123",
        job_status="active",
        verification_status="verified",
    )
    db.add(job)
    db.flush()

    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Software Engineer Resume",
    )
    db.add(resume)
    db.flush()

    resume_version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="candidate_resume.pdf",
        file_type="pdf",
        file_size=10240,
        storage_path="/tmp/fake_candidate_resume.pdf",
        parsing_status="parsed",
        parsed_content={"skills": ["Python", "FastAPI", "PostgreSQL"]},
        raw_text=(
            "Software engineer skilled in Python, FastAPI, PostgreSQL, Docker. "
            "Built scalable microservices and RESTful APIs."
        ),
    )
    db.add(resume_version)
    resume.current_version_id = resume_version.id
    db.flush()

    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=resume_version.id,
        provider="deterministic",
        model="v1.0",
        status="completed",
        result={
            "profile": {
                "summary": "Software Engineer skilled in Python, FastAPI, and PostgreSQL.",
                "domains": ["Backend Development", "Web Services"],
                "career_level_estimate": "Junior (0-2 years evidenced)",
                "evidence": [
                    {
                        "section": "Summary",
                        "excerpt": "Software engineer skilled in Python and FastAPI",
                    },
                ],
            },
            "skills": {
                "categorized_skills": {
                    "Languages": ["Python"],
                    "Backend": ["FastAPI", "PostgreSQL", "Redis"],
                },
                "supported_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
                "unevidenced_skills": [],
                "evidence": [
                    {"section": "Skills", "excerpt": "Python, FastAPI, PostgreSQL, Redis"},
                ],
            },
            "experience_evidence": {
                "summary": "Demonstrated experience building backend microservices.",
                "measurable_outcomes": ["Scaled APIs to 10k RPS"],
                "vague_or_unsupported_claims": [],
                "evidence": [
                    {
                        "section": "Experience",
                        "excerpt": (
                            "Built scalable microservices and RESTful APIs using "
                            "FastAPI and PostgreSQL."
                        ),
                        "context": "Backend Engineer",
                    }
                ],
            },
            "strengths": [],
            "improvement_opportunities": [],
            "role_suitability": [],
            "recommendations": [],
        },
    )
    db.add(analysis)
    db.commit()

    return user, company, job, resume, resume_version


# ============================================================================
# 1. Token Encryption & Decryption Tests
# ============================================================================


def test_token_encryption_roundtrip():
    secret_token = "ya29.a0ARrdaM-sensitive-access-token-123456789"
    encrypted = encrypt_token(secret_token)
    assert encrypted != secret_token
    assert len(encrypted) > 20

    decrypted = decrypt_token(encrypted)
    assert decrypted == secret_token


def test_token_decryption_invalid():
    with pytest.raises(InvalidToken):
        decrypt_token("invalid-tampered-token")


# ============================================================================
# 2. OAuth State CSRF Protection Tests
# ============================================================================


def test_oauth_state_generation_and_verification():
    user_id = uuid.uuid4()
    state = generate_oauth_state(user_id=user_id)
    assert state is not None

    payload = verify_oauth_state(state, expected_user_id=user_id)
    assert payload is not None
    assert payload["uid"] == str(user_id)
    assert payload["act"] == "gmail_connect"


def test_oauth_state_tampering_rejected():
    user_id = uuid.uuid4()
    state = generate_oauth_state(user_id=user_id)
    tampered_state = state[:-5] + "XXXXX"

    with pytest.raises(BadRequestError):
        verify_oauth_state(tampered_state, expected_user_id=user_id)


def test_oauth_state_expiry():
    user_id = uuid.uuid4()
    state = generate_oauth_state(user_id=user_id)
    # Verifying with max_age_seconds=-1 simulates expired state
    with pytest.raises(BadRequestError):
        verify_oauth_state(state, expected_user_id=user_id, max_age_seconds=-1)


# ============================================================================
# 3. Google OAuth & Gmail Integration API Tests
# ============================================================================


def test_google_auth_url(client: TestClient, db_session: Session):
    headers, _ = create_user_and_auth(client, "oauth_test@example.com")
    with patch.object(settings, "GOOGLE_CLIENT_ID", "mock-google-client-id"):
        resp = client.get("/api/v1/integrations/google/auth-url", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]
        assert "state" in data


def test_google_status_disconnected_by_default(client: TestClient, db_session: Session):
    headers, _ = create_user_and_auth(client, "disconnected@example.com")
    resp = client.get("/api/v1/integrations/google/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_connected"] is False
    assert data["email"] is None


def test_google_callback_and_disconnect(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "callback_user@example.com")
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None

    state = generate_oauth_state(user_id=user.id)

    mock_conn = GmailConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        email="applicant.google@example.com",
        encrypted_access_token=encrypt_token("ya29.mock"),
        encrypted_refresh_token=encrypt_token("1//mock"),
        scopes=["https://www.googleapis.com/auth/gmail.compose"],
        is_active=True,
        connected_at=datetime.now(timezone.utc),
    )

    with patch.object(GmailService, "exchange_code_for_tokens", return_value=mock_conn):
        callback_resp = client.post(
            "/api/v1/integrations/google/callback",
            headers=headers,
            json={"code": "mock-auth-code-123", "state": state},
        )
        assert callback_resp.status_code == 200
        cb_data = callback_resp.json()
        assert cb_data["is_connected"] is True
        assert cb_data["email"] == "applicant.google@example.com"

    # Status check with saved active connection
    db_session.add(mock_conn)
    db_session.commit()

    status_resp = client.get("/api/v1/integrations/google/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_connected"] is True

    # Disconnect integration
    with patch.object(GmailService, "disconnect_account"):
        disc_resp = client.post("/api/v1/integrations/google/disconnect", headers=headers)
        assert disc_resp.status_code == 200
        assert "disconnected" in disc_resp.json()["message"]


# ============================================================================
# 4. Application Preparation Workspace Tests
# ============================================================================


def test_application_preparation_lifecycle(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "prep_user@example.com")
    user, company, job, resume, resume_version = setup_assistant_entities(db_session, email)

    # 1. Initialize preparation
    init_resp = client.post(
        "/api/v1/application-assistant/preparations",
        headers=headers,
        json={"job_id": str(job.id), "resume_version_id": str(resume_version.id)},
    )
    assert init_resp.status_code == 200
    prep_data = init_resp.json()
    assert prep_data["job_id"] == str(job.id)
    assert prep_data["checklist_status"] in ["not_started", "in_progress"]
    assert len(prep_data["checklist_items"]) > 0

    prep_id = prep_data["id"]

    # 2. Update checklist item
    chk_resp = client.patch(
        f"/api/v1/application-assistant/preparations/{prep_id}/checklist",
        headers=headers,
        json={"item_id": "review_job", "completed": True},
    )
    assert chk_resp.status_code == 200
    updated_items = chk_resp.json()["checklist_items"]
    rev_item = next(it for it in updated_items if it["id"] == "review_job")
    assert rev_item["completed"] is True


# ============================================================================
# 5. Cover Letter Generator & PDF Export Tests
# ============================================================================


def test_cover_letter_generation_and_export(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "cl_user@example.com")
    user, company, job, resume, resume_version = setup_assistant_entities(db_session, email)

    # 1. Generate Cover Letter
    gen_resp = client.post(
        "/api/v1/application-assistant/cover-letters/generate",
        headers=headers,
        json={
            "job_id": str(job.id),
            "resume_version_id": str(resume_version.id),
            "user_instructions": "Highlight fast learning and microservices architecture.",
        },
    )
    assert gen_resp.status_code == 200
    cl_data = gen_resp.json()
    assert cl_data["opening"] is not None
    assert len(cl_data["body_paragraphs"]) > 0
    assert cl_data["closing"] is not None
    assert cl_data["is_approved"] is False

    cl_id = cl_data["id"]

    # 2. Edit Cover Letter
    edit_resp = client.patch(
        f"/api/v1/application-assistant/cover-letters/{cl_id}",
        headers=headers,
        json={"content": "Updated content: Enthusiastic about joining TechCorp Dynamics."},
    )
    assert edit_resp.status_code == 200
    assert "Enthusiastic about joining" in edit_resp.json()["content"]

    # 3. Approve Cover Letter
    appr_resp = client.patch(
        f"/api/v1/application-assistant/cover-letters/{cl_id}",
        headers=headers,
        json={"is_approved": True},
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["is_approved"] is True

    # 4. Export PDF
    pdf_resp = client.get(
        f"/api/v1/application-assistant/cover-letters/{cl_id}/pdf",
        headers=headers,
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 500  # valid PDF generated


# ============================================================================
# 6. Recruiter Email Generator, Draft, Explicit Send & Duplicate Prevention
# ============================================================================


def test_recruiter_email_workflow(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "email_user@example.com")
    user, company, job, resume, resume_version = setup_assistant_entities(db_session, email)

    # 1. Generate Recruiter Email (Nexora does not guess email)
    gen_resp = client.post(
        "/api/v1/application-assistant/emails/generate",
        headers=headers,
        json={
            "job_id": str(job.id),
            "email_type": "recruiter_outreach",
            "recipient_name": "Priya Sharma",
            "recipient_email": None,  # Nexora never guesses recruiter emails
        },
    )
    assert gen_resp.status_code == 200
    email_data = gen_resp.json()
    assert email_data["email_type"] == "recruiter_outreach"
    assert email_data["recipient_email"] is None
    assert "TechCorp Dynamics" in email_data["subject"]
    email_id = email_data["id"]

    # 2. Provide recipient email and approve
    update_resp = client.patch(
        f"/api/v1/application-assistant/emails/{email_id}",
        headers=headers,
        json={"recipient_email": "priya.sharma@techcorp.example.com"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["recipient_email"] == "priya.sharma@techcorp.example.com"

    appr_resp = client.post(
        f"/api/v1/application-assistant/emails/{email_id}/approve",
        headers=headers,
        json={"confirm_approval": True},
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"

    # 3. Simulate Gmail Connection
    conn = GmailConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        email="email_user@gmail.com",
        encrypted_access_token=encrypt_token("mock-access-token"),
        encrypted_refresh_token=encrypt_token("mock-refresh-token"),
        token_expiry=datetime.now(timezone.utc),
        is_active=True,
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(conn)
    db_session.commit()

    # 4. Create Draft via Gmail
    with patch.object(
        GmailService,
        "create_draft",
        return_value={"draft_id": "draft_abc123", "message_id": "msg_draft_123"},
    ):
        draft_resp = client.post(
            f"/api/v1/application-assistant/emails/{email_id}/gmail-draft",
            headers=headers,
        )
        assert draft_resp.status_code == 200
        assert draft_resp.json()["gmail_draft_id"] == "draft_abc123"

    # 5. Send Email WITHOUT explicit confirm_send=True MUST FAIL (Safety requirement)
    bad_send_resp = client.post(
        f"/api/v1/application-assistant/emails/{email_id}/send",
        headers=headers,
        json={"confirm_send": False},
    )
    assert bad_send_resp.status_code == 403

    # 6. Send Email WITH explicit confirm_send=True succeeds
    with patch.object(
        GmailService,
        "send_email",
        return_value={"message_id": "msg_sent_99999", "thread_id": "thread_123"},
    ):
        send_resp = client.post(
            f"/api/v1/application-assistant/emails/{email_id}/send",
            headers=headers,
            json={"confirm_send": True},
        )
        assert send_resp.status_code == 200
        assert send_resp.json()["status"] == "sent"
        assert send_resp.json()["gmail_message_id"] == "msg_sent_99999"

    # 7. Duplicate Send Prevention MUST FAIL (Duplicate-send prevention)
    dup_resp = client.post(
        f"/api/v1/application-assistant/emails/{email_id}/send",
        headers=headers,
        json={"confirm_send": True},
    )
    assert dup_resp.status_code == 400
    assert "already sent" in str(dup_resp.json()).lower()


# ============================================================================
# 7. Common Application Questions Q&A Tests (Grounding & Missing Info)
# ============================================================================


def test_application_qa_generation(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "qa_user@example.com")
    user, company, job, resume, resume_version = setup_assistant_entities(db_session, email)

    resp = client.post(
        "/api/v1/application-assistant/qa/generate",
        headers=headers,
        json={"job_id": str(job.id), "resume_version_id": str(resume_version.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    items = data["items"]
    assert len(items) >= 4

    # Notice period or compensation question should flag missing_info
    missing_items = [it for it in items if it.get("missing_info") is not None]
    assert len(missing_items) > 0


# ============================================================================
# 8. Application Portal Assistance & Explicit Confirmation
# ============================================================================


def test_portal_open_never_auto_submits(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "portal_user@example.com")
    user, company, job, resume, resume_version = setup_assistant_entities(db_session, email)

    # 1. Initialize preparation
    init_resp = client.post(
        "/api/v1/application-assistant/preparations",
        headers=headers,
        json={"job_id": str(job.id), "resume_version_id": str(resume_version.id)},
    )
    prep_data = init_resp.json()
    prep_id = prep_data["id"]

    # 2. Record portal opened
    open_resp = client.post(
        f"/api/v1/application-assistant/preparations/{prep_id}/portal-opened",
        headers=headers,
    )
    assert open_resp.status_code == 200
    prep_after_open = open_resp.json()
    assert prep_after_open["portal_opened_at"] is not None
    # CRITICAL RULE: Opening portal must NEVER mark application as submitted
    assert prep_after_open["submission_confirmed_at"] is None

    # 3. Explicitly confirm submission
    conf_resp = client.post(
        "/api/v1/application-assistant/preparations/confirm-submission",
        headers=headers,
        json={"job_id": str(job.id), "preparation_id": str(prep_id), "confirm_submission": True},
    )
    assert conf_resp.status_code == 200
    prep_after_confirm = conf_resp.json()
    assert prep_after_confirm["submission_confirmed_at"] is not None
    assert prep_after_confirm["checklist_status"] == "completed"
