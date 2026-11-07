"""
Comprehensive integration and unit tests for the Learning Roadmaps & Skill Development module.
Covers skill gap analysis, roadmap generation, milestone progression, curated resources,
activity tracking, practical project tracking, analytics, tenant isolation, and fallback.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.analysis import ResumeAnalysis
from app.models.company import Company
from app.models.interview_prep import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewPreparationSession,
    InterviewQuestion,
)
from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.models.recommendation import JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.user import User

# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def create_user_with_token(
    client: TestClient, db_session: Session, email_prefix: str = "learner"
) -> tuple[User, dict[str, str]]:
    u = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed_pw_test_123",
        full_name="Learner Test User",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    token = create_access_token(subject=str(u.id))
    headers = {"Authorization": f"Bearer {token}"}
    return u, headers


# ---------------------------------------------------------------------------
# Test 1: Empty Dataset Skill Gap Analysis & Disclosures
# ---------------------------------------------------------------------------


def test_empty_skill_gap_analysis(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "empty_learner")

    res = client.get("/api/v1/learning-roadmaps/skill-gaps", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["demonstrated_skills"] == []
    assert data["partially_demonstrated_skills"] == []
    assert data["interview_weakness_skills"] == []
    assert "verified resume evidence" in data["analysis_disclaimer"].lower()
    assert data["total_identified_gaps"] >= 0


# ---------------------------------------------------------------------------
# Test 2: Grounded Skill Gap Categorization & Prioritization
# ---------------------------------------------------------------------------


def test_skill_gap_prioritization_and_categorization(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "gap_user")

    # 1. Demonstrated skill via ResumeAnalysis
    resume = Resume(user_id=user.id, title="Test Resume")
    db_session.add(resume)
    db_session.flush()
    rv = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        original_filename="resume.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/test/path",
        raw_text="Experienced in Python and SQL.",
        parsed_content={"skills": ["Python", "SQL"]},
    )
    db_session.add(rv)
    db_session.flush()
    ra = ResumeAnalysis(
        user_id=user.id,
        resume_id=resume.id,
        version_id=rv.id,
        status="completed",
        provider="deterministic",
        model="rule_based",
        result={
            "skills_analysis": {
                "supported_skills": [{"skill_name": "Python"}, {"skill_name": "SQL"}]
            }
        },
    )
    db_session.add(ra)

    # 2. Target career preferences
    pref = UserMatchingPreference(
        user_id=user.id,
        target_role_families=["backend_python"],
        preferred_skills=["Docker", "FastAPI"],
    )
    db_session.add(pref)

    # 3. Market demand jobs requesting FastAPI, Docker, and PostgreSQL
    company_name = f"Tech Co {uuid.uuid4().hex[:6]}"
    company = Company(
        name=company_name,
        normalized_name=company_name.lower(),
        website_url="https://tech.example.com",
    )
    db_session.add(company)
    db_session.flush()
    job = Job(
        company_id=company.id,
        title="Backend SDE",
        normalized_title="backend sde",
        description="Looking for FastAPI and Docker developers",
        job_url=f"https://tech.example.com/jobs/{uuid.uuid4().hex[:6]}",
        job_status="active",
    )
    db_session.add(job)
    db_session.flush()
    ji = JobIntelligence(
        job_id=job.id,
        content_hash="test_hash_123",
        provider="deterministic",
        model="rule_based",
        status="completed",
        required_skills=["FastAPI", "Docker", "PostgreSQL"],
        preferred_skills=["Redis"],
    )
    db_session.add(ji)

    # 4. Interview weakness in Redis
    session = InterviewPreparationSession(
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title="Backend Tech Interview",
        interview_type="technical",
        interview_round="technical_round_1",
        difficulty="intermediate",
        category="technical",
        status="completed",
    )
    db_session.add(session)
    db_session.flush()
    q = InterviewQuestion(
        session_id=session.id,
        category="backend_python",
        difficulty="intermediate",
        question_text="Explain Redis caching strategies.",
        question_order=1,
    )
    db_session.add(q)
    db_session.flush()

    ans = InterviewAnswer(
        id=uuid.uuid4(),
        session_id=session.id,
        question_id=q.id,
        user_id=user.id,
        answer_text="Redis is an in-memory key-value cache.",
    )
    db_session.add(ans)
    db_session.flush()

    ev = InterviewEvaluation(
        session_id=session.id,
        answer_id=ans.id,
        overall_score=50.0,
        missing_points=["Candidate lacked knowledge of Redis cache invalidation"],
        suggested_improvements=["Review Redis TTL and caching patterns"],
        stronger_answer_example="Use cache-aside pattern",
        evaluation_feedback="Review Redis TTL and caching patterns",
        provider="deterministic",
        model="rule_based",
    )
    db_session.add(ev)
    db_session.commit()

    # Call endpoint
    res = client.get("/api/v1/learning-roadmaps/skill-gaps", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Verify demonstrated skills
    demo_skills = [s["skill"].lower() for s in data["demonstrated_skills"]]
    assert "python" in demo_skills
    assert "sql" in demo_skills

    # Verify missing skills identified from market demand
    missing_skills = [s["skill"].lower() for s in data["missing_skills"]]
    assert "fastapi" in missing_skills
    assert "docker" in missing_skills
    assert "postgresql" in missing_skills

    # Verify interview weakness detected
    weak_skills = [s["skill"].lower() for s in data["interview_weakness_skills"]]
    assert "redis" in weak_skills

    # Top recommended skills should prioritize critical/high gaps
    top_recommended = [s["skill"].lower() for s in data["top_recommended_skills"]]
    assert len(top_recommended) > 0
    # Python & SQL should not be in top recommendations because already demonstrated
    assert "python" not in top_recommended


# ---------------------------------------------------------------------------
# Test 3: Roadmap Generation & Adaptation to Candidate Resume Evidence
# ---------------------------------------------------------------------------


def test_roadmap_generation_and_adaptation(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "roadmap_user")

    # Give candidate demonstrated Python & Git skills in resume
    resume = Resume(user_id=user.id, title="Python Resume")
    db_session.add(resume)
    db_session.flush()
    rv = ResumeVersion(
        resume_id=resume.id,
        version_number=1,
        original_filename="resume.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/test/path",
        raw_text="2 years Python and Git experience.",
        parsed_content={"skills": ["Python", "Git"]},
    )
    db_session.add(rv)
    db_session.flush()
    ra = ResumeAnalysis(
        user_id=user.id,
        resume_id=resume.id,
        version_id=rv.id,
        status="completed",
        provider="deterministic",
        model="rule_based",
        result={
            "skills_analysis": {
                "supported_skills": [{"skill_name": "Python"}, {"skill_name": "Git"}]
            }
        },
    )
    db_session.add(ra)
    db_session.commit()

    # Generate Python backend roadmap
    payload = {
        "target_role": "backend_python",
        "custom_skills": ["Celery", "Kafka"],
        "target_difficulty": "intermediate",
        "user_notes": "Focusing on distributed microservices",
    }
    res = client.post("/api/v1/learning-roadmaps", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["target_role"] == "backend_python"
    assert "FastAPI" in data["target_skills"]
    assert "Kafka" in data["target_skills"]
    assert "Python" in data["already_mastered_skills"]
    assert data["total_estimated_hours"] > 0
    assert len(data["milestones"]) == 4

    # Milestones verification
    stages = [m["stage"] for m in data["milestones"]]
    assert "beginner" in stages
    assert "intermediate" in stages
    assert "advanced" in stages
    assert "portfolio" in stages

    for m in data["milestones"]:
        assert len(m["learning_objectives"]) >= 2
        assert len(m["practical_exercises"]) >= 1


# ---------------------------------------------------------------------------
# Test 4: Roadmap Lifecycle (List, Get, Status Update, Delete)
# ---------------------------------------------------------------------------


def test_roadmap_lifecycle(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "lifecycle_user")

    # Create roadmap
    create_res = client.post(
        "/api/v1/learning-roadmaps",
        json={"target_role": "fullstack", "target_difficulty": "intermediate"},
        headers=headers,
    )
    assert create_res.status_code == 201
    roadmap_id = create_res.json()["id"]

    # List roadmaps
    list_res = client.get("/api/v1/learning-roadmaps", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["id"] == roadmap_id

    # Get roadmap detail
    detail_res = client.get(f"/api/v1/learning-roadmaps/{roadmap_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == roadmap_id
    assert len(detail_res.json()["milestones"]) == 4

    # Update status to paused
    pause_res = client.patch(
        f"/api/v1/learning-roadmaps/{roadmap_id}/status",
        json={"status": "paused"},
        headers=headers,
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "paused"

    # Delete roadmap
    del_res = client.delete(f"/api/v1/learning-roadmaps/{roadmap_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_after = client.get(f"/api/v1/learning-roadmaps/{roadmap_id}", headers=headers)
    assert get_after.status_code == 404


# ---------------------------------------------------------------------------
# Test 5: Milestone Progress & Automatic Roadmap Progress Recalculation
# ---------------------------------------------------------------------------


def test_milestone_progress_and_recalculation(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "milestone_user")

    create_res = client.post(
        "/api/v1/learning-roadmaps",
        json={"target_role": "genai"},
        headers=headers,
    )
    assert create_res.status_code == 201
    roadmap = create_res.json()
    first_milestone = roadmap["milestones"][0]
    m_id = first_milestone["id"]

    # Mark milestone as in_progress with hours
    patch_res = client.patch(
        f"/api/v1/learning-roadmaps/milestones/{m_id}",
        json={
            "status": "completed",
            "completed_hours": 15.0,
            "completion_notes": "Finished document embeddings and prompt evaluations",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_m = patch_res.json()
    assert updated_m["status"] == "completed"
    assert updated_m["completed_hours"] == 15.0
    assert updated_m["completion_notes"] is not None

    # Verify parent roadmap recalculated progress
    parent_res = client.get(f"/api/v1/learning-roadmaps/{roadmap['id']}", headers=headers)
    assert parent_res.status_code == 200
    parent = parent_res.json()
    assert parent["completed_hours"] >= 15.0
    assert parent["completion_percentage"] > 0.0


# ---------------------------------------------------------------------------
# Test 6: Curated Educational Resources & Custom Bookmarks
# ---------------------------------------------------------------------------


def test_learning_resources_catalog_and_custom_bookmarks(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "resource_user")

    # 1. Browse curated resources
    res = client.get("/api/v1/learning-roadmaps/resources/catalog", headers=headers)
    assert res.status_code == 200
    resources = res.json()
    assert len(resources) > 0
    # Must preserve original reputable URLs
    assert any("docs.python.org" in r["url"] for r in resources)
    assert any("fastapi.tiangolo.com" in r["url"] for r in resources)

    # Filter by skill
    py_res = client.get("/api/v1/learning-roadmaps/resources/catalog?skill=Python", headers=headers)
    assert py_res.status_code == 200
    for r in py_res.json():
        assert "python" in r["skill"].lower()

    # 2. Add custom bookmark
    custom_payload = {
        "skill": "Redis",
        "title": "Redis Pub/Sub Architecture Guide",
        "provider": "Redis Official Blog",
        "url": "https://redis.io/docs/latest/develop/interact/pubsub/",
        "cost_tier": "free",
        "resource_type": "tutorial",
        "difficulty": "intermediate",
        "estimated_hours": 3.0,
        "description": "Deep-dive into asynchronous messaging patterns",
    }
    create_res = client.post(
        "/api/v1/learning-roadmaps/resources/custom",
        json=custom_payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    custom_obj = create_res.json()
    assert custom_obj["is_curated"] is False
    assert custom_obj["title"] == "Redis Pub/Sub Architecture Guide"

    # Delete custom bookmark
    del_res = client.delete(
        f"/api/v1/learning-roadmaps/resources/custom/{custom_obj['id']}",
        headers=headers,
    )
    assert del_res.status_code == 204


# ---------------------------------------------------------------------------
# Test 7: Activity Logging & Study Time Tracking
# ---------------------------------------------------------------------------


def test_activity_logging_and_history(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "activity_user")

    # Log study session
    act_payload = {
        "skill": "FastAPI",
        "activity_type": "coding",
        "hours_spent": 2.5,
        "notes": "Implemented custom Pydantic validators and JWT token refresh",
    }
    log_res = client.post("/api/v1/learning-roadmaps/activities", json=act_payload, headers=headers)
    assert log_res.status_code == 201
    act_data = log_res.json()
    assert act_data["skill"] == "FastAPI"
    assert act_data["hours_spent"] == 2.5

    # List activities
    history_res = client.get("/api/v1/learning-roadmaps/activities", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 1
    assert history[0]["skill"] == "FastAPI"


# ---------------------------------------------------------------------------
# Test 8: Practical Project Recommendations & Portfolio Tracking
# ---------------------------------------------------------------------------


def test_practical_project_recommendations_and_tracking(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "project_user")

    # 1. Project recommendations
    rec_res = client.get(
        "/api/v1/learning-roadmaps/projects/recommendations?target_role=backend_python",
        headers=headers,
    )
    assert rec_res.status_code == 200
    recommendations = rec_res.json()
    assert len(recommendations) >= 1
    sample = recommendations[0]
    assert "title" in sample
    assert "objective" in sample
    assert len(sample["tech_stack"]) > 0
    assert len(sample["functional_requirements"]) > 0
    assert len(sample["suggested_milestones"]) > 0

    # 2. Track project
    proj_payload = {
        "title": sample["title"],
        "objective": sample["objective"],
        "tech_stack": sample["tech_stack"],
        "target_skills": sample["target_skills"],
        "functional_requirements": sample["functional_requirements"],
        "status": "in_progress",
    }
    create_proj = client.post(
        "/api/v1/learning-roadmaps/projects", json=proj_payload, headers=headers
    )
    assert create_proj.status_code == 201
    proj_obj = create_proj.json()
    assert proj_obj["status"] == "in_progress"
    assert proj_obj["portfolio_ready"] is False

    # 3. Update project with repository and demo URL
    update_payload = {
        "repository_url": "https://github.com/testuser/distributed-job-processor",
        "live_demo_url": "https://processor.example.com",
        "architecture_summary": "FastAPI + Celery + Redis worker cluster with Docker Compose.",
        "evidence_notes": "Implemented sliding-window rate limiting with Redis Lua scripts.",
        "status": "completed",
        "portfolio_ready": True,
    }
    patch_proj = client.patch(
        f"/api/v1/learning-roadmaps/projects/{proj_obj['id']}",
        json=update_payload,
        headers=headers,
    )
    assert patch_proj.status_code == 200
    updated_proj = patch_proj.json()
    assert updated_proj["status"] == "completed"
    assert updated_proj["portfolio_ready"] is True
    assert updated_proj["repository_url"] == "https://github.com/testuser/distributed-job-processor"

    # 4. List projects
    list_p = client.get("/api/v1/learning-roadmaps/projects", headers=headers)
    assert list_p.status_code == 200
    assert len(list_p.json()) >= 1


# ---------------------------------------------------------------------------
# Test 9: Learning Analytics Synthesis
# ---------------------------------------------------------------------------


def test_learning_analytics_synthesis(client: TestClient, db_session: Session):
    user, headers = create_user_with_token(client, db_session, "analytics_user")

    # Add study activity
    client.post(
        "/api/v1/learning-roadmaps/activities",
        json={"skill": "PostgreSQL", "hours_spent": 4.0, "activity_type": "practice"},
        headers=headers,
    )
    # Add roadmap
    client.post(
        "/api/v1/learning-roadmaps",
        json={"target_role": "data_analyst"},
        headers=headers,
    )

    analytics_res = client.get("/api/v1/learning-roadmaps/analytics", headers=headers)
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    assert data["total_learning_hours"] >= 4.0
    assert data["active_roadmaps_count"] >= 1
    assert "PostgreSQL" in data["hours_by_skill"]
    assert "readiness_contribution_summary" in data


# ---------------------------------------------------------------------------
# Test 10: Multi-Tenant Cross-User Isolation & Security
# ---------------------------------------------------------------------------


def test_learning_roadmap_tenant_isolation(client: TestClient, db_session: Session):
    user_a, headers_a = create_user_with_token(client, db_session, "user_a")
    user_b, headers_b = create_user_with_token(client, db_session, "user_b")

    # User A creates roadmap
    res_a = client.post(
        "/api/v1/learning-roadmaps",
        json={"target_role": "sde"},
        headers=headers_a,
    )
    assert res_a.status_code == 201
    roadmap_a_id = res_a.json()["id"]
    milestone_a_id = res_a.json()["milestones"][0]["id"]

    # User A creates custom bookmark
    custom_res = client.post(
        "/api/v1/learning-roadmaps/resources/custom",
        json={
            "skill": "C++",
            "title": "C++ Concurrency in Action",
            "provider": "Manning",
            "url": "https://manning.com/books/c-plus-plus-concurrency-in-action",
        },
        headers=headers_a,
    )
    custom_a_id = custom_res.json()["id"]

    # User A creates project
    proj_res = client.post(
        "/api/v1/learning-roadmaps/projects",
        json={
            "title": "Private Project",
            "objective": "A private project for User A",
            "tech_stack": ["Python"],
            "target_skills": ["Python"],
        },
        headers=headers_a,
    )
    proj_a_id = proj_res.json()["id"]

    # 1. User B cannot view User A's roadmap (404)
    res_b_get = client.get(f"/api/v1/learning-roadmaps/{roadmap_a_id}", headers=headers_b)
    assert res_b_get.status_code == 404

    # 2. User B cannot update User A's milestone (404)
    res_b_m = client.patch(
        f"/api/v1/learning-roadmaps/milestones/{milestone_a_id}",
        json={"status": "completed"},
        headers=headers_b,
    )
    assert res_b_m.status_code == 404

    # 3. User B cannot delete User A's roadmap (404)
    res_b_del = client.delete(f"/api/v1/learning-roadmaps/{roadmap_a_id}", headers=headers_b)
    assert res_b_del.status_code == 404

    # 4. User B cannot delete User A's custom resource (404)
    res_b_del_res = client.delete(
        f"/api/v1/learning-roadmaps/resources/custom/{custom_a_id}",
        headers=headers_b,
    )
    assert res_b_del_res.status_code == 404

    # 5. User B cannot update User A's project (404)
    res_b_patch_proj = client.patch(
        f"/api/v1/learning-roadmaps/projects/{proj_a_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert res_b_patch_proj.status_code == 404

    # 6. Unauthenticated requests receive 401 Unauthorized
    assert client.get("/api/v1/learning-roadmaps/skill-gaps").status_code == 401
    assert client.get("/api/v1/learning-roadmaps").status_code == 401
    assert client.get("/api/v1/learning-roadmaps/resources/catalog").status_code == 401
    assert client.get("/api/v1/learning-roadmaps/activities").status_code == 401
    assert client.get("/api/v1/learning-roadmaps/projects").status_code == 401
    assert client.get("/api/v1/learning-roadmaps/analytics").status_code == 401
