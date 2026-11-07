import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application import JobApplication
from app.models.networking import NetworkingContact, RecruiterProfile
from app.models.notification import Notification
from app.models.orchestration import CopilotSession
from app.models.portfolio import Portfolio, PortfolioSection, PortfolioVersion
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


def get_authenticated_user(
    client: TestClient, email: str, full_name: str
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": full_name,
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def test_cross_user_resume_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot view, download, or delete User A's resumes."""
    headers_a, email_a = get_authenticated_user(client, "alice_resume@test.com", "Alice")
    headers_b, email_b = get_authenticated_user(client, "bob_resume@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    resume_a = Resume(
        id=uuid.uuid4(),
        user_id=user_a.id,
        title="Alice's Private Resume",
    )
    db_session.add(resume_a)
    db_session.flush()

    ver_a = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume_a.id,
        version_number=1,
        original_filename="alice_resume.pdf",
        storage_path=f"{user_a.id}/{resume_a.id}/alice_resume.pdf",
        file_type="pdf",
        file_size=1024,
        parsing_status="parsed",
    )
    db_session.add(ver_a)
    resume_a.current_version_id = ver_a.id
    db_session.commit()

    # User A can view their resume
    res_a = client.get(f"/api/v1/resumes/{resume_a.id}", headers=headers_a)
    assert res_a.status_code == 200

    # User B CANNOT view Alice's resume
    res_b = client.get(f"/api/v1/resumes/{resume_a.id}", headers=headers_b)
    assert res_b.status_code == 404

    # User B CANNOT download Alice's resume
    res_b_dl = client.get(f"/api/v1/resumes/{resume_a.id}/download", headers=headers_b)
    assert res_b_dl.status_code == 404

    # User B CANNOT delete Alice's resume
    res_b_del = client.delete(f"/api/v1/resumes/{resume_a.id}", headers=headers_b)
    assert res_b_del.status_code == 404


def test_cross_user_application_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot access, modify, or delete User A's job applications."""
    headers_a, email_a = get_authenticated_user(client, "alice_app@test.com", "Alice")
    headers_b, _ = get_authenticated_user(client, "bob_app@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    app_a = JobApplication(
        id=uuid.uuid4(),
        user_id=user_a.id,
        status="interview",
        title="Software Engineer",
        company_name="Acme Corp",
        notes="Secret salary negotiation notes",
    )
    db_session.add(app_a)
    db_session.commit()

    # User A can access application
    res_a = client.get(f"/api/v1/applications/{app_a.id}", headers=headers_a)
    assert res_a.status_code == 200

    # User B receives 404 on attempt to read Alice's application
    res_b = client.get(f"/api/v1/applications/{app_a.id}", headers=headers_b)
    assert res_b.status_code == 404

    # User B receives 404 on attempt to update Alice's application status
    res_b_patch = client.patch(
        f"/api/v1/applications/{app_a.id}",
        json={"status": "rejected"},
        headers=headers_b,
    )
    assert res_b_patch.status_code == 404

    # User B receives 404 on attempt to delete Alice's application
    res_b_del = client.delete(f"/api/v1/applications/{app_a.id}", headers=headers_b)
    assert res_b_del.status_code == 404


def test_cross_user_networking_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot view or tamper with User A's private networking CRM contacts."""
    headers_a, email_a = get_authenticated_user(client, "alice_net@test.com", "Alice")
    headers_b, _ = get_authenticated_user(client, "bob_net@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    recruiter = RecruiterProfile(
        id=uuid.uuid4(),
        full_name="Sarah Talent",
        normalized_name="sarah talent",
        company_name="Google",
        source_type="official_careers_page",
    )
    db_session.add(recruiter)
    db_session.flush()

    contact_a = NetworkingContact(
        id=uuid.uuid4(),
        user_id=user_a.id,
        recruiter_id=recruiter.id,
        relationship_status="outreach_prepared",
        networking_notes="Alice spoke to Sarah at conference",
    )
    db_session.add(contact_a)
    db_session.commit()

    # User A can update contact
    res_a = client.patch(
        f"/api/v1/networking/crm/contacts/{contact_a.id}",
        json={"networking_notes": "Alice updated notes"},
        headers=headers_a,
    )
    assert res_a.status_code == 200
    assert res_a.json()["networking_notes"] == "Alice updated notes"

    # User B cannot update Alice's contact (IDOR protected)
    res_b = client.patch(
        f"/api/v1/networking/crm/contacts/{contact_a.id}",
        json={"networking_notes": "Hacked by Bob"},
        headers=headers_b,
    )
    assert res_b.status_code == 404

    # User B cannot delete Alice's contact
    res_b_del = client.delete(
        f"/api/v1/networking/crm/contacts/{contact_a.id}",
        headers=headers_b,
    )
    assert res_b_del.status_code == 404

    # User B's CRM overview does not include Alice's contact
    res_b_crm = client.get("/api/v1/networking/crm/overview", headers=headers_b)
    assert res_b_crm.status_code == 200
    contacts_b = res_b_crm.json().get("contacts", [])
    assert not any(c["id"] == str(contact_a.id) for c in contacts_b)


def test_cross_user_matching_preferences_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot read or overwrite User A's job matching preferences."""
    headers_a, email_a = get_authenticated_user(client, "alice_pref@test.com", "Alice")
    headers_b, email_b = get_authenticated_user(client, "bob_pref@test.com", "Bob")

    # Alice sets target roles
    payload_a = {
        "target_role_families": ["backend_engineer"],
        "preferred_locations": ["Remote", "Bengaluru"],
        "min_salary": 2000000,
    }
    client.put("/api/v1/matches/preferences", json=payload_a, headers=headers_a)

    # Bob sets completely different preferences
    payload_b = {
        "target_role_families": ["frontend_engineer"],
        "preferred_locations": ["London"],
        "min_salary": 80000,
    }
    client.put("/api/v1/matches/preferences", json=payload_b, headers=headers_b)

    # Verify Alice's preferences remain intact
    alice_get = client.get("/api/v1/matches/preferences", headers=headers_a)
    assert alice_get.status_code == 200
    data_a = alice_get.json()
    assert "backend_engineer" in data_a["target_role_families"]
    assert "frontend_engineer" not in data_a["target_role_families"]


def test_cross_user_copilot_session_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot access or message User A's private AI Copilot conversations."""
    headers_a, email_a = get_authenticated_user(client, "alice_copilot@test.com", "Alice")
    headers_b, _ = get_authenticated_user(client, "bob_copilot@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    session_a = CopilotSession(
        id=uuid.uuid4(),
        user_id=user_a.id,
        title="Alice's Executive Salary Discussion",
    )
    db_session.add(session_a)
    db_session.commit()

    # User A accesses session
    res_a = client.get(f"/api/v1/copilot/sessions/{session_a.id}", headers=headers_a)
    assert res_a.status_code == 200

    # User B receives 404
    res_b = client.get(f"/api/v1/copilot/sessions/{session_a.id}", headers=headers_b)
    assert res_b.status_code == 404

    # User B cannot post message to Alice's session
    res_b_post = client.post(
        f"/api/v1/copilot/sessions/{session_a.id}/messages",
        json={"content": "Malicious prompt injection"},
        headers=headers_b,
    )
    assert res_b_post.status_code == 404

    # User B cannot delete Alice's session
    res_b_del = client.delete(f"/api/v1/copilot/sessions/{session_a.id}", headers=headers_b)
    assert res_b_del.status_code == 404


def test_cross_user_portfolio_version_restore_isolation(
    client: TestClient, db_session: Session
) -> None:
    """Verify User B cannot restore User A's portfolio version snapshot."""
    headers_a, email_a = get_authenticated_user(client, "alice_port@test.com", "Alice")
    headers_b, _ = get_authenticated_user(client, "bob_port@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    portfolio_a = Portfolio(
        id=uuid.uuid4(),
        user_id=user_a.id,
        public_slug=f"alice-{uuid.uuid4().hex[:8]}",
        title="Alice's Tech Portfolio",
        is_published=False,
    )
    db_session.add(portfolio_a)
    db_session.flush()

    ver_a = PortfolioVersion(
        id=uuid.uuid4(),
        portfolio_id=portfolio_a.id,
        version_number=1,
        change_summary="Initial design",
        snapshot_json={"title": "Alice V1 Title"},
    )
    db_session.add(ver_a)
    db_session.commit()

    # User B attempts to restore Alice's snapshot ID
    res_b_restore = client.post(
        f"/api/v1/portfolios/versions/{ver_a.id}/restore",
        headers=headers_b,
    )
    assert res_b_restore.status_code == 404


def test_cross_user_notifications_isolation(client: TestClient, db_session: Session) -> None:
    """Verify User B cannot view or mark User A's notifications as read."""
    headers_a, email_a = get_authenticated_user(client, "alice_notif@test.com", "Alice")
    headers_b, _ = get_authenticated_user(client, "bob_notif@test.com", "Bob")

    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    notif_a = Notification(
        id=uuid.uuid4(),
        user_id=user_a.id,
        notification_type="interview_reminder",
        title="Alice's Amazon Final Round",
        message="Your interview starts at 2:00 PM",
        is_read=False,
    )
    db_session.add(notif_a)
    db_session.commit()

    # User B list does not show Alice's notification
    res_b_list = client.get("/api/v1/notifications", headers=headers_b)
    assert res_b_list.status_code == 200
    b_items = res_b_list.json().get("notifications", [])
    assert not any(n["id"] == str(notif_a.id) for n in b_items)

    # User B cannot mark Alice's notification as read
    res_b_read = client.patch(f"/api/v1/notifications/{notif_a.id}/read", headers=headers_b)
    assert res_b_read.status_code == 404


def test_public_portfolio_privacy_and_unpublishing(client: TestClient, db_session: Session) -> None:
    """Verify public portfolio exposes only published, visible data and strictly
    returns 404 when unpublished.
    """
    headers_a, email_a = get_authenticated_user(client, "alice_pub@test.com", "Alice")
    user_a = db_session.query(User).filter(User.email == email_a).first()
    assert user_a is not None

    unique_slug = f"alice-engineer-{uuid.uuid4().hex[:8]}"

    # Initially unpublished
    portfolio = Portfolio(
        id=uuid.uuid4(),
        user_id=user_a.id,
        public_slug=unique_slug,
        title="Alice Senior Portfolio",
        headline="AI Research Engineer",
        is_published=False,
        profile_data={"email": "alice_public@example.com", "github": "https://github.com/alice"},
    )
    db_session.add(portfolio)
    db_session.flush()

    sec_visible = PortfolioSection(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        section_type="skills",
        title="Core Technical Skills",
        content_json={"skills": ["Python", "PyTorch"]},
        is_visible=True,
    )
    sec_hidden = PortfolioSection(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        section_type="custom",
        title="Internal Draft Notes",
        content_json={"notes": "Draft not ready for public view"},
        is_visible=False,
    )
    db_session.add(sec_visible)
    db_session.add(sec_hidden)
    db_session.commit()

    # 1. Unauthenticated request while unpublished MUST return 404
    res_pub_private = client.get(f"/api/v1/portfolios/public/{unique_slug}")
    assert res_pub_private.status_code == 404

    # 2. Alice publishes her portfolio
    pub_res = client.post("/api/v1/portfolios/publish", headers=headers_a)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # Get updated public slug from Alice's published portfolio
    alice_slug = pub_res.json()["public_slug"]

    # 3. Public access succeeds now
    res_pub_active = client.get(f"/api/v1/portfolios/public/{alice_slug}")
    assert res_pub_active.status_code == 200
    data = res_pub_active.json()

    # Verify sensitive IDs and hidden sections are stripped
    assert "user_id" not in data
    assert "id" not in data
    section_titles = [s["title"] for s in data["sections"]]
    assert "Core Technical Skills" in section_titles
    assert "Internal Draft Notes" not in section_titles

    # 4. Alice unpublishes
    unpub_res = client.post("/api/v1/portfolios/unpublish", headers=headers_a)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["is_published"] is False

    # 5. Public access immediately revokes to 404
    res_pub_revoked = client.get(f"/api/v1/portfolios/public/{alice_slug}")
    assert res_pub_revoked.status_code == 404
