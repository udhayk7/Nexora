import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.company import Company
from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.models.networking import (
    NetworkingContact,
    RecruiterProfile,
)
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


def _create_user(db: Session, email_prefix: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Alex Candidate",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _create_company_and_job(
    db: Session,
    company_name: str = "Stripe",
    category: str = "product",
    job_title: str = "Junior Software Engineer",
) -> tuple[Company, Job]:
    comp = Company(
        id=uuid.uuid4(),
        name=company_name,
        normalized_name=company_name.lower().strip(),
        category=category,
        verification_status="verified",
        website_url="https://stripe.com",
        careers_url="https://stripe.com/jobs",
    )
    db.add(comp)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=comp.id,
        title=job_title,
        normalized_title=job_title.lower().strip(),
        description="We are seeking an entry-level Python engineer.",
        location_text="Bengaluru, India",
        work_arrangement="hybrid",
        seniority_level="entry",
        skills_tags=["Python", "FastAPI", "PostgreSQL", "Docker"],
        job_status="active",
        verification_status="verified",
        job_url=f"https://{comp.normalized_name}.example.com/jobs/123",
        application_url=f"https://{comp.normalized_name}.example.com/jobs/apply/123",
    )
    db.add(job)
    db.commit()
    db.refresh(comp)
    db.refresh(job)
    return comp, job


def _create_resume_with_skills(db: Session, user: User) -> tuple[Resume, ResumeVersion]:
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Software Engineer Resume",
    )
    db.add(resume)
    db.flush()

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        storage_path="/resumes/alex_resume.pdf",
        original_filename="alex_resume.pdf",
        file_type="pdf",
        file_size=1024,
        parsing_status="parsed",
        parsed_content={
            "contact": {
                "name": user.full_name,
                "email": user.email,
                "phone": "+91 9876543210",
                "location": "Bengaluru, India",
                "links": ["https://linkedin.com/in/alex", "https://github.com/alex"],
            },
            "summary": "Junior Software Engineer specializing in Python and FastAPI architectures.",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Git"],
            "projects": [
                {
                    "title": "Distributed Cloud Task Engine",
                    "description": "High-throughput asynchronous task queue using Celery.",
                }
            ],
            "experience": [],
            "education": [],
        },
    )
    db.add(version)
    resume.current_version_id = version.id
    db.commit()
    db.refresh(resume)
    db.refresh(version)
    return resume, version


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


def test_recruiter_discovery_and_company_seeding(client: TestClient, db_session: Session):
    """Test Case 1: Discover company recruitment team and seed profiles."""
    user = _create_user(db_session, "disco_user")
    headers = _get_auth_headers(user)
    comp, job = _create_company_and_job(db_session, "Uber", "product")

    # Discover recruiters for company
    res = client.post(
        f"/api/v1/networking/recruiters/discover-company/{comp.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    recruiter = data[0]
    assert "Uber" in recruiter["company_name"]
    assert recruiter["verification_status"] == "verified"
    assert recruiter["source_type"] == "official_careers_page"


def test_manual_recruiter_creation_and_deduplication(client: TestClient, db_session: Session):
    """Test Case 2: Candidate manual recruiter addition with deduplication and validation."""
    user = _create_user(db_session, "manual_user")
    headers = _get_auth_headers(user)
    comp, _ = _create_company_and_job(db_session, "Google", "product")

    payload = {
        "full_name": "Priya Sharma",
        "designation": "Staff Technical Recruiter",
        "company_id": str(comp.id),
        "company_name": "Google",
        "recruitment_specialization": "Backend Engineering & AI",
        "relevant_departments": ["Engineering", "AI Research"],
        "public_profile_url": "https://linkedin.com/in/priyasharma-recruiter",
        "contact_email": "priya.recruiter@google.example.com",
    }

    # 1. First creation
    res1 = client.post("/api/v1/networking/recruiters", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["full_name"] == "Priya Sharma"
    assert data1["verification_status"] == "unverified"

    # 2. Second creation with same normalized name and company should deduplicate
    res2 = client.post("/api/v1/networking/recruiters", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["id"] == data1["id"]  # Deduplicated to same recruiter

    # 3. Invalid email rejected
    invalid_payload = {**payload, "full_name": "New Recruiter", "contact_email": "notanemail"}
    bad_res = client.post("/api/v1/networking/recruiters", json=invalid_payload, headers=headers)
    assert bad_res.status_code == 422


def test_recruiter_matching_and_explainable_ranking(client: TestClient, db_session: Session):
    """Test Case 3: Intelligent recruiter matching with multi-dimensional scoring."""
    user = _create_user(db_session, "match_user")
    headers = _get_auth_headers(user)
    _create_resume_with_skills(db_session, user)

    # Set preferred matching company & roles
    pref = UserMatchingPreference(
        user_id=user.id,
        target_role_families=["Software Engineer", "Backend Developer"],
        preferred_locations=["Bengaluru"],
        work_arrangement_preferences=["hybrid"],
        metadata_json={"target_companies": ["Amazon"]},
    )
    db_session.add(pref)

    comp, job = _create_company_and_job(db_session, "Amazon", "product")

    # Create recruiter aligned with target company and skills
    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Karthik Raman",
        normalized_name="karthik raman",
        designation="Lead Technical Recruiter",
        company_id=comp.id,
        company_name="Amazon",
        recruitment_specialization="Python, Cloud Infrastructure & Backend Engineering",
        relevant_departments=["Engineering"],
        associated_job_ids=[str(job.id)],
        verification_status="verified",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    # Query discovery with matching
    res = client.get("/api/v1/networking/recruiters?query=Karthik", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    match_item = next(
        (item for item in data["items"] if item["recruiter"]["full_name"] == "Karthik Raman"), None
    )
    assert match_item is not None
    assert match_item["match"]["match_score"] >= 70.0
    assert match_item["match"]["company_relevance"] == "preferred_target_company"
    assert len(match_item["match"]["match_reasons"]) >= 2


def test_ai_outreach_generation_multi_types(client: TestClient, db_session: Session):
    """Test Case 4: Generating grounded drafts across multiple networking message types."""
    user = _create_user(db_session, "outreach_user")
    headers = _get_auth_headers(user)
    _create_resume_with_skills(db_session, user)
    comp, job = _create_company_and_job(db_session, "Microsoft", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Sarah Jenkins",
        normalized_name="sarah jenkins",
        designation="Senior University Recruiter",
        company_id=comp.id,
        company_name="Microsoft",
        recruitment_specialization="University Graduate Software Engineering",
        relevant_departments=["Engineering"],
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    message_types = [
        "recruiter_intro",
        "job_inquiry",
        "internship_inquiry",
        "follow_up",
        "interview_thank_you",
        "networking_email",
    ]

    for mtype in message_types:
        payload = {
            "recruiter_id": str(rec.id),
            "message_type": mtype,
            "channel": "email",
            "tone": "professional",
            "job_id": str(job.id),
        }
        res = client.post("/api/v1/networking/outreach/generate", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["message_type"] == mtype
        assert data["status"] == "draft"
        assert len(data["body"]) > 20
        assert "Sarah" in data["body"]
        assert len(data["grounded_claims"]) >= 1


def test_linkedin_character_limit_enforcement(client: TestClient, db_session: Session):
    """Test Case 5: LinkedIn connection note strictly enforces <= 300 characters."""
    user = _create_user(db_session, "linkedin_user")
    headers = _get_auth_headers(user)
    _create_resume_with_skills(db_session, user)
    comp, _ = _create_company_and_job(db_session, "Apple", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="David Miller",
        normalized_name="david miller",
        company_id=comp.id,
        company_name="Apple",
        designation="iOS & Backend Talent Lead",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    payload = {
        "recruiter_id": str(rec.id),
        "message_type": "linkedin_connection",
        "channel": "linkedin",
        "tone": "concise",
        "enforce_linkedin_char_limit": True,
    }
    res = client.post("/api/v1/networking/outreach/generate", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["message_type"] == "linkedin_connection"
    assert len(data["body"]) <= 300
    assert data["character_count"] <= 300


def test_candidate_approval_gate_for_outreach(client: TestClient, db_session: Session):
    """Test Case 6: Explicit candidate review & approval gate for outreach messages."""
    user = _create_user(db_session, "approve_user")
    headers = _get_auth_headers(user)
    _create_resume_with_skills(db_session, user)
    comp, job = _create_company_and_job(db_session, "Meta", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Jessica Alba",
        normalized_name="jessica alba",
        company_id=comp.id,
        company_name="Meta",
        contact_email="jessica.recruiter@meta.example.com",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    # 1. Generate draft
    gen_res = client.post(
        "/api/v1/networking/outreach/generate",
        json={
            "recruiter_id": str(rec.id),
            "message_type": "recruiter_intro",
            "channel": "email",
        },
        headers=headers,
    )
    assert gen_res.status_code == 200
    msg_id = gen_res.json()["id"]

    # 2. Approve draft with edited body
    approve_res = client.post(
        f"/api/v1/networking/outreach/messages/{msg_id}/approve",
        json={
            "edited_subject": "Customized Introduction regarding Meta AI",
            "edited_body": (
                "Hi Jessica, I am excited to connect regarding software roles at Meta."
            ),
        },
        headers=headers,
    )
    assert approve_res.status_code == 200
    appr_data = approve_res.json()
    assert appr_data["status"] == "approved"
    assert appr_data["approval_confirmed_at"] is not None
    assert "Customized Introduction" in appr_data["subject"]


def test_gmail_send_explicit_confirmation_required(client: TestClient, db_session: Session):
    """Test Case 7: Sending outreach email via Gmail strictly requires confirm_send=True."""
    user = _create_user(db_session, "gmail_user")
    headers = _get_auth_headers(user)
    resume, ver = _create_resume_with_skills(db_session, user)
    comp, job = _create_company_and_job(db_session, "Netflix", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Emily Watson",
        normalized_name="emily watson",
        company_id=comp.id,
        company_name="Netflix",
        contact_email="emily.recruiter@netflix.example.com",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    # Generate and approve message
    gen_res = client.post(
        "/api/v1/networking/outreach/generate",
        json={"recruiter_id": str(rec.id), "message_type": "job_inquiry", "channel": "email"},
        headers=headers,
    )
    msg_id = gen_res.json()["id"]

    client.post(
        f"/api/v1/networking/outreach/messages/{msg_id}/approve",
        json={"edited_body": "Hi Emily, I am enthusiastically applying for the software role."},
        headers=headers,
    )

    # 1. Attempt send without confirm_send should be rejected with 400
    fail_res = client.post(
        f"/api/v1/networking/outreach/messages/{msg_id}/send-gmail",
        json={"confirm_send": False},
        headers=headers,
    )
    assert fail_res.status_code == 400

    # 2. Send with confirm_send=True and mocked GmailService
    with patch("app.services.networking_crm_service.GmailService.send_email") as mock_send:
        mock_send.return_value = {"status": "sent", "message_id": "gmail_msg_12345"}
        success_res = client.post(
            f"/api/v1/networking/outreach/messages/{msg_id}/send-gmail",
            json={"confirm_send": True, "attach_resume": True},
            headers=headers,
        )
        assert success_res.status_code == 200
        s_data = success_res.json()
        assert s_data["status"] == "success"
        assert s_data["gmail_message_id"] == "gmail_msg_12345"
        mock_send.assert_called_once()


def test_crm_relationship_lifecycle_and_activities(client: TestClient, db_session: Session):
    """Test Case 8: CRM relationship state transitions and activity tracking."""
    user = _create_user(db_session, "crm_user")
    headers = _get_auth_headers(user)
    comp, job = _create_company_and_job(db_session, "Adobe", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Aman Verma",
        normalized_name="aman verma",
        company_id=comp.id,
        company_name="Adobe",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    # 1. Add to CRM (status = saved)
    add_res = client.post(
        "/api/v1/networking/crm/contacts",
        json={
            "recruiter_id": str(rec.id),
            "relationship_status": "saved",
            "networking_notes": "Met at career fair",
        },
        headers=headers,
    )
    assert add_res.status_code == 201
    contact_data = add_res.json()
    contact_id = contact_data["id"]
    assert contact_data["relationship_status"] == "saved"
    assert len(contact_data["recent_activities"]) >= 1

    # 2. Update status to contacted
    patch_res = client.patch(
        f"/api/v1/networking/crm/contacts/{contact_id}",
        json={
            "relationship_status": "contacted",
            "communication_channel": "linkedin",
            "next_follow_up_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    p_data = patch_res.json()
    assert p_data["relationship_status"] == "contacted"
    assert p_data["initial_contact_date"] is not None

    # 3. Record response received
    resp_res = client.patch(
        f"/api/v1/networking/crm/contacts/{contact_id}",
        json={"response_status": "positive"},
        headers=headers,
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["relationship_status"] == "responded"


def test_duplicate_crm_prevention(client: TestClient, db_session: Session):
    """Test Case 9: Attempting to save same recruiter twice updates single relationship."""
    user = _create_user(db_session, "dedup_user")
    headers = _get_auth_headers(user)
    comp, _ = _create_company_and_job(db_session, "Salesforce", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Chloe Bennett",
        normalized_name="chloe bennett",
        company_id=comp.id,
        company_name="Salesforce",
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    res1 = client.post(
        "/api/v1/networking/crm/contacts",
        json={"recruiter_id": str(rec.id), "relationship_status": "saved"},
        headers=headers,
    )
    res2 = client.post(
        "/api/v1/networking/crm/contacts",
        json={"recruiter_id": str(rec.id), "relationship_status": "contacted"},
        headers=headers,
    )
    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["id"] == res2.json()["id"]

    # Verify only 1 contact in database for this user
    count = (
        db_session.query(NetworkingContact).filter_by(user_id=user.id, recruiter_id=rec.id).count()
    )
    assert count == 1


def test_follow_up_intelligence_and_reminders(client: TestClient, db_session: Session):
    """Test Case 10: Follow-up intelligence surfaces contacts requiring follow-up."""
    user = _create_user(db_session, "followup_user")
    headers = _get_auth_headers(user)
    comp, _ = _create_company_and_job(db_session, "Cisco", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Rajesh Kumar",
        normalized_name="rajesh kumar",
        company_id=comp.id,
        company_name="Cisco",
        is_global=True,
    )
    db_session.add(rec)
    db_session.flush()

    past_date = datetime.now(timezone.utc) - timedelta(days=7)
    contact = NetworkingContact(
        id=uuid.uuid4(),
        user_id=user.id,
        recruiter_id=rec.id,
        company_id=comp.id,
        relationship_status="contacted",
        initial_contact_date=past_date,
        last_contact_date=past_date,
        next_follow_up_date=past_date + timedelta(days=5),  # Overdue by 2 days
    )
    db_session.add(contact)
    db_session.commit()

    # Query due follow-ups
    res = client.get("/api/v1/networking/follow-ups/due", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_due"] >= 1
    item = next((i for i in data["items"] if str(i["relationship_id"]) == str(contact.id)), None)
    assert item is not None
    assert item["days_since_last_contact"] >= 7
    assert item["suggested_message_type"] == "follow_up"


def test_multi_user_data_isolation(client: TestClient, db_session: Session):
    """Test Case 11: Multi-tenant CRM isolation between users."""
    user_a = _create_user(db_session, "tenant_a")
    user_b = _create_user(db_session, "tenant_b")
    headers_a = _get_auth_headers(user_a)
    headers_b = _get_auth_headers(user_b)
    comp, _ = _create_company_and_job(db_session, "Intuit", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Private Recruiter",
        normalized_name="private recruiter",
        company_id=comp.id,
        company_name="Intuit",
        is_global=False,
        created_by_user_id=user_a.id,
    )
    db_session.add(rec)
    db_session.flush()

    # User A adds to CRM
    contact_a = NetworkingContact(
        id=uuid.uuid4(),
        user_id=user_a.id,
        recruiter_id=rec.id,
        company_id=comp.id,
        relationship_status="saved",
    )
    db_session.add(contact_a)
    db_session.commit()

    # User A sees 1 saved recruiter
    dash_a = client.get("/api/v1/networking/crm/overview", headers=headers_a).json()
    assert dash_a["saved_recruiters_count"] == 1

    # User B should NOT see User A's private contact
    dash_b = client.get("/api/v1/networking/crm/overview", headers=headers_b).json()
    assert dash_b["saved_recruiters_count"] == 0

    # User B cannot update User A's contact
    del_res = client.delete(f"/api/v1/networking/crm/contacts/{contact_a.id}", headers=headers_b)
    assert del_res.status_code == 404


def test_no_guessing_email_policy(client: TestClient, db_session: Session):
    """Test Case 12: Cannot send email if recruiter has no verified email address."""
    user = _create_user(db_session, "no_guess_user")
    headers = _get_auth_headers(user)
    comp, _ = _create_company_and_job(db_session, "Oracle", "product")

    rec = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Mark Spencer",
        normalized_name="mark spencer",
        company_id=comp.id,
        company_name="Oracle",
        contact_email=None,  # No verified email
        is_global=True,
    )
    db_session.add(rec)
    db_session.commit()

    gen_res = client.post(
        "/api/v1/networking/outreach/generate",
        json={"recruiter_id": str(rec.id), "message_type": "recruiter_intro", "channel": "email"},
        headers=headers,
    )
    msg_id = gen_res.json()["id"]

    # Attempting to send email without verified email address should fail with 400
    send_res = client.post(
        f"/api/v1/networking/outreach/messages/{msg_id}/send-gmail",
        json={"confirm_send": True},
        headers=headers,
    )
    assert send_res.status_code == 400
    res_json = send_res.json()
    detail = res_json.get("detail") or res_json.get("error", {}).get("message", "")
    assert "forbids guessing" in detail.lower() or "not available" in detail.lower()
