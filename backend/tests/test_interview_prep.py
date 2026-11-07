import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.analysis import ResumeAnalysis
from app.models.company import Company
from app.models.job import Job
from app.models.notification import Notification
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.services.ai.interview_evaluation_engine import SafeStaticCodeAnalyzer


def create_user_and_auth(
    client: TestClient, email: str = "interviewee@example.com"
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Interview Candidate",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_interview_entities(
    db: Session, user_email: str
) -> tuple[User, Company, Job, Resume, ResumeVersion, ResumeAnalysis]:
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=user_email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Interview Candidate",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="Apex Cloud Networks",
        normalized_name="apex cloud networks",
        website_url="https://apexcloud.example.com",
        normalized_domain="apexcloud.example.com",
        category="product_company",
    )
    db.add(company)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Backend Software Engineer",
        normalized_title="backend software engineer",
        description=(
            "We are seeking an engineer experienced in Python, FastAPI, PostgreSQL, "
            "and Redis for building high-scale distributed backend services."
        ),
        skills_tags=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
        seniority_level="entry_level",
        work_arrangement="remote",
        job_url="https://apexcloud.example.com/careers/123",
        application_url="https://apexcloud.example.com/careers/123",
        job_status="active",
        verification_status="verified",
    )
    db.add(job)
    db.flush()

    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Candidate Resume",
    )
    db.add(resume)
    db.flush()

    resume_version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="candidate.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/tmp/candidate.pdf",
        parsing_status="parsed",
        parsed_content={"skills": ["Python", "FastAPI", "PostgreSQL"]},
        raw_text="Built distributed task queues and APIs with Python and PostgreSQL.",
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
                "summary": "Software engineer skilled in Python and PostgreSQL.",
                "domains": ["Backend"],
                "career_level_estimate": "Junior",
                "evidence": [{"section": "Summary", "excerpt": "Software engineer in Python"}],
            },
            "skills": {
                "categorized_skills": {"Languages": ["Python"]},
                "supported_skills": ["Python", "FastAPI", "PostgreSQL"],
                "unevidenced_skills": [],
                "evidence": [{"section": "Skills", "excerpt": "Python, FastAPI, PostgreSQL"}],
            },
            "experience_evidence": {
                "summary": "Engineered distributed APIs.",
                "measurable_outcomes": ["Reduced latency by 40%"],
                "vague_or_unsupported_claims": [],
                "evidence": [
                    {
                        "section": "Distributed Task Scheduler",
                        "excerpt": "Engineered distributed task queue using Python and PostgreSQL.",
                    }
                ],
            },
            "education": {"degrees": [], "institutions": [], "evidence": []},
            "certifications": {"certifications": [], "evidence": []},
            "overall_quality_assessment": {"score": 85, "summary": "Strong"},
        },
    )
    db.add(analysis)
    db.commit()
    db.refresh(user)
    db.refresh(job)

    return user, company, job, resume, resume_version, analysis


def test_create_session_and_plan_generation(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_1@example.com")
    user, company, job, resume, version, analysis = setup_interview_entities(db_session, email)

    payload = {
        "job_id": str(job.id),
        "interview_round": "technical",
        "interview_type": "mock_interview",
        "category": "technical",
        "difficulty": "intermediate",
        "question_count": 3,
        "user_instructions": "Focus on connection pooling and async execution.",
    }

    resp = client.post("/api/v1/interview-prep/sessions", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["user_id"] == str(user.id)
    assert data["job_id"] == str(job.id)
    assert data["category"] == "technical"
    assert data["difficulty"] == "intermediate"
    assert data["total_questions"] == 3
    assert len(data["questions"]) == 3
    assert data["status"] == "in_progress"

    # Preparation plan verification
    plan = data["preparation_plan"]
    assert plan is not None
    assert "technical_topics_to_revise" in plan
    assert "relevant_projects_to_explain" in plan
    assert "potential_skill_gaps" in plan


def test_question_generation_different_categories(
    client: TestClient, db_session: Session
) -> None:
    headers, email = create_user_and_auth(client, "prep_user_2@example.com")
    setup_interview_entities(db_session, email)

    categories = [
        "coding_problem_solving",
        "backend_python",
        "behavioral_hr",
        "system_design",
        "database_sql",
    ]

    for cat in categories:
        payload = {
            "interview_round": "technical",
            "category": cat,
            "difficulty": "beginner",
            "question_count": 2,
        }
        resp = client.post("/api/v1/interview-prep/sessions", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["questions"]) == 2
        for q in data["questions"]:
            assert q["category"] == cat
            assert q["difficulty"] == "beginner"
            assert "expected_points" in q
            assert len(q["expected_points"]) > 0


def test_answer_submission_and_rubric_evaluation(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_3@example.com")
    setup_interview_entities(db_session, email)

    # 1. Create Session
    create_resp = client.post(
        "/api/v1/interview-prep/sessions",
        json={"category": "database_sql", "difficulty": "intermediate", "question_count": 2},
        headers=headers,
    )
    assert create_resp.status_code == 201
    session_data = create_resp.json()
    session_id = session_data["id"]
    q1 = session_data["questions"][0]

    # 2. Submit Answer
    answer_payload = {
        "answer_text": (
            "The N+1 query problem occurs when an application executes an initial query "
            "for parent records, followed by N separate queries for related child records. "
            "In PostgreSQL with SQLAlchemy, this is resolved using joinedload or selectinload, "
            "which batches the fetch into 1 or 2 queries and avoids excessive database round trips."
        ),
        "time_spent_seconds": 90,
    }

    sub_resp = client.post(
        f"/api/v1/interview-prep/sessions/{session_id}/questions/{q1['id']}/answer",
        json=answer_payload,
        headers=headers,
    )
    assert sub_resp.status_code == 200, sub_resp.text
    sub_data = sub_resp.json()

    # Rubric Verification
    eval_data = sub_data["evaluation"]
    assert eval_data["overall_score"] >= 60.0
    assert eval_data["technical_correctness_score"] >= 65.0
    assert eval_data["relevance_score"] >= 70.0
    assert len(eval_data["strengths"]) > 0
    assert "suggested_improvements" in eval_data

    # Session Progress verified through session detail
    sess_resp = client.get(
        f"/api/v1/interview-prep/sessions/{session_id}", headers=headers
    )
    assert sess_resp.status_code == 200
    sess = sess_resp.json()
    assert sess["completed_questions"] == 1
    assert sess["total_questions"] == 2
    assert sess["status"] == "in_progress"


def test_safe_static_code_evaluation(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_4@example.com")
    setup_interview_entities(db_session, email)

    # Verify SafeStaticCodeAnalyzer independently
    code_valid = """
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        diff = target - num
        if diff in seen:
            return [seen[diff], i]
        seen[num] = i
    return []
"""
    eval_res = SafeStaticCodeAnalyzer.analyze_python_code(code_valid)
    assert eval_res["valid_syntax"] is True
    assert "two_sum" in eval_res["functions_defined"]
    assert "loops" in eval_res["complexity_hint"]

    # Verify Syntax Error Handling without crash
    code_syntax_error = "def broken_code(:\n    return False"
    eval_err = SafeStaticCodeAnalyzer.analyze_python_code(code_syntax_error)
    assert eval_err["valid_syntax"] is False
    assert len(eval_err["issues"]) > 0

    # API Answer submission with code
    create_resp = client.post(
        "/api/v1/interview-prep/sessions",
        json={"category": "coding_problem_solving", "question_count": 1},
        headers=headers,
    )
    session_id = create_resp.json()["id"]
    q_id = create_resp.json()["questions"][0]["id"]

    sub_resp = client.post(
        f"/api/v1/interview-prep/sessions/{session_id}/questions/{q_id}/answer",
        json={
            "answer_text": "Here is an optimal single-pass hash map solution in O(N) time.",
            "submitted_code": code_valid,
            "submitted_language": "python",
        },
        headers=headers,
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["submitted_code"] is not None


def test_project_breakdown_studio(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_5@example.com")
    setup_interview_entities(db_session, email)

    payload = {
        "project_name": "Distributed Task Scheduler",
        "user_instructions": "Focus on database locking, task retries, and worker concurrency.",
    }

    resp = client.post(
        "/api/v1/interview-prep/project-breakdown",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["project_name"] == "Distributed Task Scheduler"
    assert "overview_pitch" in data
    assert "architecture_and_design" in data
    assert len(data["technical_implementation"]) > 0
    assert len(data["key_challenges_and_solutions"]) > 0
    assert len(data["practice_questions"]) > 0


def test_notes_crud_and_pinning(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_6@example.com")
    setup_interview_entities(db_session, email)

    # 1. Create note
    create_payload = {
        "title": "PostgreSQL Indexing Revision",
        "content": "Review difference between B-Tree and GIN indexes for JSONB columns.",
        "note_type": "topics_to_revise",
        "is_pinned": False,
    }
    create_resp = client.post(
        "/api/v1/interview-prep/notes", json=create_payload, headers=headers
    )
    assert create_resp.status_code == 201
    note_id = create_resp.json()["id"]

    # 2. List notes
    list_resp = client.get("/api/v1/interview-prep/notes", headers=headers)
    assert list_resp.status_code == 200
    notes = list_resp.json()
    assert any(n["id"] == note_id for n in notes)

    # 3. Update & pin note
    update_resp = client.put(
        f"/api/v1/interview-prep/notes/{note_id}",
        json={"is_pinned": True, "title": "PostgreSQL Indexing [PRIORITY]"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_pinned"] is True

    # 4. Delete note
    del_resp = client.delete(f"/api/v1/interview-prep/notes/{note_id}", headers=headers)
    assert del_resp.status_code == 204


def test_analytics_aggregation(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_7@example.com")
    setup_interview_entities(db_session, email)

    # Create and answer 1 question
    create_resp = client.post(
        "/api/v1/interview-prep/sessions",
        json={"category": "technical", "question_count": 1},
        headers=headers,
    )
    session_id = create_resp.json()["id"]
    q_id = create_resp.json()["questions"][0]["id"]

    client.post(
        f"/api/v1/interview-prep/sessions/{session_id}/questions/{q_id}/answer",
        json={
            "answer_text": (
                "Value types live on the stack with deterministic lifetime while reference "
                "types live on the heap and are managed by garbage collection pauses."
            )
        },
        headers=headers,
    )

    analytics_resp = client.get("/api/v1/interview-prep/analytics", headers=headers)
    assert analytics_resp.status_code == 200
    data = analytics_resp.json()

    assert data["total_sessions_started"] >= 1
    assert data["total_questions_attempted"] >= 1
    assert data["overall_average_score"] > 0
    assert len(data["category_performance"]) > 0


def test_schedule_reminder(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_auth(client, "prep_user_8@example.com")
    user, company, job, resume, version, analysis = setup_interview_entities(db_session, email)

    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {
        "scheduled_at": future_time,
        "reminder_type": "interview_reminder",
        "custom_message": "Revise B-Tree indexing and Celery concurrency before tomorrow's round.",
    }

    resp = client.post("/api/v1/interview-prep/reminders", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None

    # Verify notification created in DB
    notif = db_session.query(Notification).filter(Notification.user_id == user.id).first()
    assert notif is not None
    assert notif.notification_type == "interview_reminder"


def test_missing_resume_returns_400(client: TestClient) -> None:
    headers, _ = create_user_and_auth(client, "no_resume_user@example.com")
    resp = client.post(
        "/api/v1/interview-prep/sessions",
        json={"category": "technical"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "resume" in resp.text.lower()


def test_user_isolation(client: TestClient, db_session: Session) -> None:
    headers1, email1 = create_user_and_auth(client, "user_alpha@example.com")
    setup_interview_entities(db_session, email1)

    headers2, email2 = create_user_and_auth(client, "user_beta@example.com")
    setup_interview_entities(db_session, email2)

    # User 1 creates session
    s1_resp = client.post(
        "/api/v1/interview-prep/sessions",
        json={"category": "technical", "question_count": 1},
        headers=headers1,
    )
    s1_id = s1_resp.json()["id"]

    # User 2 tries to access User 1's session -> 404
    s2_get = client.get(f"/api/v1/interview-prep/sessions/{s1_id}", headers=headers2)
    assert s2_get.status_code == 404
