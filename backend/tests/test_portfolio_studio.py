"""
Comprehensive integration and unit tests for Portfolio Studio & Professional Showcase.
Covers profile editing, project showcases, theme customization, publishing/unpublishing,
public access authorization, cross-user isolation, versioning, exports, and analytics.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.learning_roadmap import LearningProject
from app.models.user import User


def _create_user(db: Session, email_prefix: str = "portfolio_user") -> User:
    u = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="hashed_pw_test",
        full_name="Test Candidate",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _get_auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Initialization and Profile CRUD
# ---------------------------------------------------------------------------


def test_get_or_create_portfolio(client: TestClient, db_session: Session):
    user = _create_user(db_session, "init_user")
    headers = _get_auth_headers(user)

    res = client.get("/api/v1/portfolios/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["public_slug"].startswith("p_")
    assert data["is_published"] is False
    assert data["template_id"] == "minimal"
    assert len(data["sections"]) >= 6

    # Repeated call returns the same portfolio
    res2 = client.get("/api/v1/portfolios/me", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["id"] == data["id"]


def test_update_portfolio_profile(client: TestClient, db_session: Session):
    user = _create_user(db_session, "prof_user")
    headers = _get_auth_headers(user)

    update_payload = {
        "title": "Jane Doe — Principal Systems Architect",
        "headline": "Distributed Systems & Cloud Engineer",
        "profile_data": {
            "full_name": "Jane Doe",
            "headline": "Distributed Systems & Cloud Engineer",
            "summary": "Building fault-tolerant systems in Python & Rust.",
            "location": "San Francisco, CA",
            "target_roles": ["Distributed Systems Engineer"],
            "technical_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
            "contact_email": "jane@example.com",
            "github_url": "https://github.com/janedoe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "education": [
                {
                    "institution": "Stanford University",
                    "degree": "B.S. in Computer Science",
                    "field_of_study": "Systems",
                    "start_year": 2020,
                    "end_year": 2024,
                    "highlights": ["Dean's Honor List"],
                }
            ],
            "work_experience": [
                {
                    "company": "Tech Corp",
                    "role": "Software Engineer",
                    "location": "SF",
                    "start_date": "2024-01",
                    "is_current": True,
                    "description": "Led backend microservices migration.",
                    "bullet_points": ["Improved throughput by 40%."],
                }
            ],
            "certifications": [],
            "achievements": [],
        },
    }

    res = client.put("/api/v1/portfolios/profile", json=update_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Jane Doe — Principal Systems Architect"
    assert data["profile_data"]["full_name"] == "Jane Doe"
    assert len(data["profile_data"]["technical_skills"]) == 5
    assert len(data["profile_data"]["work_experience"]) == 1


# ---------------------------------------------------------------------------
# 2. Template and Theme Customization
# ---------------------------------------------------------------------------


def test_update_portfolio_theme(client: TestClient, db_session: Session):
    user = _create_user(db_session, "theme_user")
    headers = _get_auth_headers(user)

    payload = {
        "template_id": "developer",
        "theme_config": {
            "accent_color": "#10B981",
            "font_family": "mono",
            "dark_mode": "dark",
            "show_contact_form": False,
            "show_view_counter": True,
        },
        "custom_css": ".custom-hero { padding: 2rem; }",
    }

    res = client.put("/api/v1/portfolios/theme", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["template_id"] == "developer"
    assert data["theme_config"]["accent_color"] == "#10B981"
    assert data["theme_config"]["font_family"] == "mono"
    assert data["custom_css"] == ".custom-hero { padding: 2rem; }"

    # Invalid template
    bad_payload = dict(payload)
    bad_payload["template_id"] = "invalid_template"
    bad_res = client.put("/api/v1/portfolios/theme", json=bad_payload, headers=headers)
    assert bad_res.status_code == 400


def test_update_public_slug(client: TestClient, db_session: Session):
    user1 = _create_user(db_session, "slug1")
    user2 = _create_user(db_session, "slug2")
    headers1 = _get_auth_headers(user1)
    headers2 = _get_auth_headers(user2)

    # Valid custom slug
    res = client.put(
        "/api/v1/portfolios/slug",
        json={"public_slug": "alex-dev-2026"},
        headers=headers1,
    )
    assert res.status_code == 200
    assert res.json()["public_slug"] == "alex-dev-2026"

    # Invalid slug (spaces, uppercase, symbols)
    bad_res = client.put(
        "/api/v1/portfolios/slug",
        json={"public_slug": "alex dev!@#"},
        headers=headers1,
    )
    assert bad_res.status_code == 400

    # Conflict check
    conflict_res = client.put(
        "/api/v1/portfolios/slug",
        json={"public_slug": "alex-dev-2026"},
        headers=headers2,
    )
    assert conflict_res.status_code == 409


# ---------------------------------------------------------------------------
# 3. Section Reordering and Visibility
# ---------------------------------------------------------------------------


def test_reorder_and_toggle_sections(client: TestClient, db_session: Session):
    user = _create_user(db_session, "sections_user")
    headers = _get_auth_headers(user)

    init_res = client.get("/api/v1/portfolios/me", headers=headers)
    sections = init_res.json()["sections"]
    assert len(sections) >= 3

    # Reverse order and hide the second section
    reorder_payload = {
        "sections": [
            {"id": sections[0]["id"], "order_index": 2, "is_visible": True},
            {"id": sections[1]["id"], "order_index": 1, "is_visible": False},
        ]
    }

    res = client.put("/api/v1/portfolios/sections", json=reorder_payload, headers=headers)
    assert res.status_code == 200

    # Verify via detail
    updated = client.get("/api/v1/portfolios/me", headers=headers).json()
    sec_map = {s["id"]: s for s in updated["sections"]}
    assert sec_map[sections[0]["id"]]["order_index"] == 2
    assert sec_map[sections[1]["id"]]["is_visible"] is False


# ---------------------------------------------------------------------------
# 4. Project Showcase CRUD & Learning Module Integration
# ---------------------------------------------------------------------------


def test_portfolio_project_crud(client: TestClient, db_session: Session):
    user = _create_user(db_session, "proj_user")
    headers = _get_auth_headers(user)

    create_payload = {
        "title": "High-Throughput Rate Limiter",
        "problem_statement": "Prevent API abuse and ensure fair multitenant capacity.",
        "description": "Distributed Token Bucket and Sliding Window algorithm with Redis.",
        "tech_stack": ["Python", "FastAPI", "Redis", "Docker"],
        "key_features": [
            "Atomic Lua script reservation",
            "Microsecond Redis server time synchronization",
        ],
        "architecture_overview": "Decoupled Redis token store with fallback memory buckets.",
        "candidate_contribution": "Architected the Lua concurrency scripts.",
        "repository_url": "https://github.com/example/rate-limiter",
        "live_demo_url": "https://demo.example.com/ratelimit",
        "challenges": "Clock drift between worker processes resolved with Redis TIME.",
        "outcomes": "Sustained 50,000 req/sec benchmark with sub-millisecond p99 latency.",
        "status": "completed",
        "is_featured": True,
        "is_visible": True,
    }

    create_res = client.post("/api/v1/portfolios/projects", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    proj_data = create_res.json()
    proj_id = proj_data["id"]
    assert proj_data["title"] == "High-Throughput Rate Limiter"
    assert proj_data["is_featured"] is True

    # Update
    update_res = client.patch(
        f"/api/v1/portfolios/projects/{proj_id}",
        json={"title": "Distributed Rate Limiter Engine", "is_featured": False},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Distributed Rate Limiter Engine"
    assert update_res.json()["is_featured"] is False

    # Delete
    del_res = client.delete(f"/api/v1/portfolios/projects/{proj_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify deleted
    portfolio_res = client.get("/api/v1/portfolios/me", headers=headers).json()
    assert all(p["id"] != proj_id for p in portfolio_res["projects"])


def test_import_from_learning_project(client: TestClient, db_session: Session):
    user = _create_user(db_session, "import_user")
    headers = _get_auth_headers(user)

    # Create a learning project in DB
    lp = LearningProject(
        user_id=user.id,
        title="Async Distributed Task Queue",
        objective="Scale backend background processing using Celery and Redis.",
        tech_stack=["Python", "FastAPI", "Celery", "Redis"],
        target_skills=["Celery", "Distributed Systems"],
        functional_requirements=["Retry backoff", "Dead letter queue"],
        status="completed",
        repository_url="https://github.com/example/async-queue",
        live_demo_url="https://queue.example.com",
        architecture_summary="Celery worker cluster consuming from partitioned Redis lists.",
        evidence_notes="Zero dropped tasks during simulated worker terminations.",
    )
    db_session.add(lp)
    db_session.commit()
    db_session.refresh(lp)

    # Import into portfolio
    res = client.post(
        f"/api/v1/portfolios/projects/import-learning/{lp.id}",
        headers=headers,
    )
    assert res.status_code == 201
    imported = res.json()
    assert imported["title"] == "Async Distributed Task Queue"
    assert imported["learning_project_id"] == str(lp.id)
    assert "Celery" in imported["tech_stack"]
    assert imported["repository_url"] == "https://github.com/example/async-queue"


# ---------------------------------------------------------------------------
# 5. Publishing and Public Access Controls
# ---------------------------------------------------------------------------


def test_publishing_lifecycle_and_public_access(client: TestClient, db_session: Session):
    user = _create_user(db_session, "pub_user")
    headers = _get_auth_headers(user)

    # 1. Fetch initial portfolio
    portfolio = client.get("/api/v1/portfolios/me", headers=headers).json()
    slug = portfolio["public_slug"]

    # 2. Public view while unpublished must return 404
    unauth_res = client.get(f"/api/v1/portfolios/public/{slug}")
    assert unauth_res.status_code == 404

    # 3. Add a visible and a hidden project
    client.post(
        "/api/v1/portfolios/projects",
        json={"title": "Public Project", "description": "Desc", "is_visible": True},
        headers=headers,
    )

    client.post(
        "/api/v1/portfolios/projects",
        json={"title": "Draft Secret Project", "description": "Desc", "is_visible": False},
        headers=headers,
    )

    # 4. Publish
    pub_res = client.post("/api/v1/portfolios/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True
    assert pub_res.json()["published_at"] is not None

    # 5. Public view now succeeds (no auth headers!)
    public_view = client.get(
        f"/api/v1/portfolios/public/{slug}",
        headers={"User-Agent": "Mozilla/5.0 (iPhone)", "Referer": "https://linkedin.com"},
    )
    assert public_view.status_code == 200
    data = public_view.json()
    assert data["public_slug"] == slug
    assert "user_id" not in data  # Privacy verification: user_id is NOT exposed!

    # Verify only visible project is returned
    proj_titles = [p["title"] for p in data["projects"]]
    assert "Public Project" in proj_titles
    assert "Draft Secret Project" not in proj_titles

    # 6. Unpublish
    unpub_res = client.post("/api/v1/portfolios/unpublish", headers=headers)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["is_published"] is False

    # 7. Public view returns 404 again
    revoked_res = client.get(f"/api/v1/portfolios/public/{slug}")
    assert revoked_res.status_code == 404


# ---------------------------------------------------------------------------
# 6. Cross-User Authorization and Isolation
# ---------------------------------------------------------------------------


def test_cross_user_isolation(client: TestClient, db_session: Session):
    user_a = _create_user(db_session, "user_a")
    user_b = _create_user(db_session, "user_b")
    headers_a = _get_auth_headers(user_a)
    headers_b = _get_auth_headers(user_b)

    # User A creates a project
    proj_a = client.post(
        "/api/v1/portfolios/projects",
        json={"title": "User A Private Project", "description": "Desc"},
        headers=headers_a,
    ).json()
    proj_a_id = proj_a["id"]

    # User B cannot update or delete User A's project
    update_res = client.patch(
        f"/api/v1/portfolios/projects/{proj_a_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert update_res.status_code == 404

    del_res = client.delete(f"/api/v1/portfolios/projects/{proj_a_id}", headers=headers_b)
    assert del_res.status_code == 404


# ---------------------------------------------------------------------------
# 7. Version History and Restore
# ---------------------------------------------------------------------------


def test_version_snapshots_and_restore(client: TestClient, db_session: Session):
    user = _create_user(db_session, "ver_user")
    headers = _get_auth_headers(user)

    # Initial state
    client.put(
        "/api/v1/portfolios/profile",
        json={
            "title": "Version 1 Title",
            "profile_data": {
                "full_name": "Original Name",
                "headline": "Junior Dev",
                "summary": "Original Summary",
                "location": "NY",
                "target_roles": ["Junior Developer"],
                "technical_skills": ["Python"],
            },
        },
        headers=headers,
    )

    # Create explicit version snapshot
    v1_res = client.post(
        "/api/v1/portfolios/versions",
        json={"change_summary": "Original State Backup"},
        headers=headers,
    )
    assert v1_res.status_code == 201
    v1_id = v1_res.json()["id"]

    # Mutate state
    client.put(
        "/api/v1/portfolios/profile",
        json={
            "title": "Version 2 Title",
            "profile_data": {
                "full_name": "Mutated Name",
                "headline": "Senior Architect",
                "summary": "Mutated Summary",
                "location": "SF",
                "target_roles": ["Principal Architect"],
                "technical_skills": ["Rust", "Distributed Systems"],
            },
        },
        headers=headers,
    )

    # Restore to Version 1
    restore_res = client.post(
        f"/api/v1/portfolios/versions/{v1_id}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    restored = restore_res.json()
    assert restored["title"] == "Version 1 Title"
    assert restored["profile_data"]["full_name"] == "Original Name"


# ---------------------------------------------------------------------------
# 8. Exports (HTML and PDF)
# ---------------------------------------------------------------------------


def test_portfolio_exports(client: TestClient, db_session: Session):
    user = _create_user(db_session, "export_user")
    headers = _get_auth_headers(user)

    # 1. HTML Export
    html_res = client.get("/api/v1/portfolios/export/html", headers=headers)
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert "<!DOCTYPE html>" in html_res.text
    assert "Nexora Portfolio Studio" in html_res.text

    # 2. PDF Export
    pdf_res = client.get("/api/v1/portfolios/export/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert pdf_res.content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# 9. AI Assistant with Deterministic Fallback
# ---------------------------------------------------------------------------


def test_ai_portfolio_assistant_fallback(client: TestClient, db_session: Session):
    user = _create_user(db_session, "ai_user")
    headers = _get_auth_headers(user)

    # Test summary improvement
    res_summary = client.post(
        "/api/v1/portfolios/ai-assist",
        json={
            "assist_type": "improve_summary",
            "current_text": "I am a backend developer writing APIs.",
            "target_role": "Backend Engineer",
        },
        headers=headers,
    )
    assert res_summary.status_code == 200
    data_summary = res_summary.json()
    assert "suggested_content" in data_summary
    assert len(data_summary["bullet_points"]) >= 1

    # Test project description generation
    res_proj = client.post(
        "/api/v1/portfolios/ai-assist",
        json={
            "assist_type": "project_description",
            "project_title": "Real-time Notification Service",
            "tech_stack": ["FastAPI", "WebSockets", "Redis"],
            "rough_notes": "Implemented pub sub to broadcast alerts with low latency.",
        },
        headers=headers,
    )
    assert res_proj.status_code == 200
    data_proj = res_proj.json()
    assert "Real-time Notification Service" in data_proj["suggested_content"]


# ---------------------------------------------------------------------------
# 10. Privacy-Conscious Analytics
# ---------------------------------------------------------------------------


def test_portfolio_analytics(client: TestClient, db_session: Session):
    user = _create_user(db_session, "analytics_user")
    headers = _get_auth_headers(user)

    # Publish portfolio
    portfolio = client.post("/api/v1/portfolios/publish", headers=headers).json()
    slug = portfolio["public_slug"]

    # Public visit with headers
    client.get(
        f"/api/v1/portfolios/public/{slug}",
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0)",
            "Referer": "https://linkedin.com/feed",
        },
    )
    # Direct visit
    client.get(f"/api/v1/portfolios/public/{slug}")

    # Record public interaction event
    client.post(
        f"/api/v1/portfolios/public/{slug}/event",
        json={"event_type": "project_view"},
    )

    # Fetch analytics
    analytics_res = client.get("/api/v1/portfolios/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_views"] >= 2
    assert analytics["project_views"] >= 1
    assert "linkedin" in analytics["referrers"]
    assert "mobile" in analytics["devices"]
