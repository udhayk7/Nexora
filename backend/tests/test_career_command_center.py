import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.analysis import ResumeAnalysis
from app.models.application import ApplicationStatusHistory, JobApplication
from app.models.assistant import ApplicationPreparation
from app.models.company import Company
from app.models.interview_prep import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewPreparationSession,
    InterviewQuestion,
)
from app.models.job import Job
from app.models.match import JobMatch
from app.models.recommendation import JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


def create_user_and_auth(
    client: TestClient,
    email: str = "command_center_user@example.com",
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Command Center Candidate",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_command_center_data(
    db: Session, user_email: str
) -> tuple[User, Company, Job, Resume, ResumeVersion]:
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=user_email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Command Center Candidate",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="Apex Cloud Systems",
        normalized_name="apex cloud systems",
        website_url="https://apexcloud.example.com",
        category="product",
    )
    db.add(company)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Backend Software Engineer",
        normalized_title="backend software engineer",
        role_family="backend_engineer",
        description="Develop microservices in Python and FastAPI.",
        job_url="https://apexcloud.example.com/careers/backend-eng",
        job_status="active",
        verification_status="verified",
        location_text="Bengaluru, India",
        work_arrangement="hybrid",
        first_seen_at=datetime.now(timezone.utc),
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

    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="resume.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="/resumes/resume.pdf",
        raw_text="Python FastAPI Docker PostgreSQL Redis Backend Systems",
        parsed_content={"skills": ["Python", "FastAPI", "PostgreSQL", "Docker"]},
    )
    db.add(version)
    db.commit()

    return user, company, job, resume, version


def test_career_overview_empty_dataset(client: TestClient, db_session: Session):
    headers, _ = create_user_and_auth(client, "empty_user@example.com")

    res = client.get("/api/v1/career-command-center/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["strong_job_matches"] == 0
    assert data["saved_opportunities"] == 0
    assert data["applications_in_progress"] == 0
    assert data["applications_submitted"] == 0
    assert data["interviews_scheduled"] == 0
    assert data["offers_received"] == 0
    assert data["weekly_application_target"] == 5
    assert data["applications_this_week"] == 0
    assert data["target_progress_percentage"] == 0.0


def test_career_overview_aggregation(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "kpi_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    # 1. Add Analysis
    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=version.id,
        status="completed",
        provider="gemini",
        model="gemini-1.5-flash",
        result={
            "skills_analysis": {
                "supported_skills": ["Python", "FastAPI", "PostgreSQL"],
                "evidence": [{"section": "Experience", "excerpt": "Built Python FastAPI APIs"}],
            }
        },
    )
    db_session.add(analysis)

    # 2. Add JobMatch (Strong Match >= 75)
    match = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        version_id=version.id,
        analysis_id=analysis.id,
        engine_version="v1.0-deterministic",
        match_score=85.0,
        score_breakdown={"skills": 85.0},
        positive_signals=[{"signal": "Python"}],
        gap_signals=[],
        is_saved=True,
    )
    db_session.add(match)

    # 3. Add Application (Applied)
    app1 = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="applied",
        submission_confirmed=True,
        applied_at=datetime.now(timezone.utc),
    )
    # 4. Add Application (Interview)
    app2 = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        company_id=company.id,
        title="Full Stack Developer",
        company_name=company.name,
        status="interview",
        submission_confirmed=True,
        applied_at=datetime.now(timezone.utc),
    )
    db_session.add_all([app1, app2])

    # 5. Add InterviewPrepSession
    prep_session = InterviewPreparationSession(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        application_id=app2.id,
        title="Mock Interview",
    )
    db_session.add(prep_session)
    db_session.commit()

    res = client.get("/api/v1/career-command-center/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["strong_job_matches"] == 1
    assert data["saved_opportunities"] == 1
    assert data["applications_in_progress"] == 1  # app2 is in 'interview'
    assert data["applications_submitted"] == 2  # app1 and app2
    assert data["interviews_scheduled"] == 1
    assert data["resume_versions_created"] == 1
    assert data["interview_prep_sessions_completed"] == 1
    assert data["applications_this_week"] == 2
    assert data["target_progress_percentage"] == 40.0  # 2 of 5 = 40%


def test_career_funnel_calculations_and_dropoff(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "funnel_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    # Add match
    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=version.id,
        status="completed",
        provider="gemini",
        model="gemini-1.5-flash",
    )
    db_session.add(analysis)

    match = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        version_id=version.id,
        analysis_id=analysis.id,
        engine_version="v1.0-deterministic",
        match_score=80.0,
        score_breakdown={},
        is_saved=True,
    )
    db_session.add(match)

    # Add application reaching interview
    app = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="interview",
        submission_confirmed=True,
        applied_at=datetime.now(timezone.utc),
    )
    db_session.add(app)
    db_session.flush()

    # Add status history
    h1 = ApplicationStatusHistory(
        id=uuid.uuid4(),
        application_id=app.id,
        from_status="preparing",
        to_status="applied",
    )
    h2 = ApplicationStatusHistory(
        id=uuid.uuid4(),
        application_id=app.id,
        from_status="applied",
        to_status="interview",
    )
    db_session.add_all([h1, h2])
    db_session.commit()

    res = client.get("/api/v1/career-command-center/funnel", headers=headers)
    assert res.status_code == 200
    data = res.json()

    stages = {s["stage_id"]: s for s in data["stages"]}
    assert stages["discovered"]["count"] >= 1
    assert stages["matched"]["count"] == 1
    assert stages["saved"]["count"] == 1
    assert stages["applied"]["count"] == 1
    assert stages["interview"]["count"] == 1
    assert stages["offer"]["count"] == 0

    # Verify drop-off from interview to offer
    assert stages["offer"]["drop_off_count"] == 1
    assert stages["offer"]["conversion_from_previous_percentage"] == 0.0

    # Verify outcomes
    assert data["outcomes"]["active"] == 1
    assert data["outcomes"]["offered"] == 0


def test_career_readiness_evidence_and_deterministic_score(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "readiness_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    # 1. Completed resume analysis with grounded evidence
    analysis = ResumeAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        resume_id=resume.id,
        version_id=version.id,
        status="completed",
        provider="gemini",
        model="gemini-1.5-flash",
        result={
            "candidate_profile": {"summary": "Backend engineer specializing in distributed APIs."},
            "skills_analysis": {
                "supported_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "categorized_skills": {
                    "Backend": ["Python", "FastAPI"],
                    "Database": ["PostgreSQL"],
                },
                "evidence": [
                    {
                        "section": "Experience",
                        "excerpt": "Engineered Python FastAPI microservices.",
                    },
                ],
            },
            "experience_evidence": {
                "measurable_outcomes": ["Reduced API latency by 45%", "Scaled to 10k RPS"]
            },
        },
    )
    db_session.add(analysis)

    # 2. Add Job Intelligence for active job market comparison
    job_intel = JobIntelligence(
        id=uuid.uuid4(),
        job_id=job.id,
        content_hash="abc123hash",
        required_skills=["Python", "FastAPI", "Kubernetes"],
        preferred_skills=["Docker", "AWS"],
        responsibilities=["Develop microservices"],
    )
    db_session.add(job_intel)

    # 3. Matching score
    match = JobMatch(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        resume_id=resume.id,
        version_id=version.id,
        analysis_id=analysis.id,
        engine_version="v1.0-deterministic",
        match_score=80.0,
        score_breakdown={},
    )
    db_session.add(match)

    # 4. Mock Interview Evaluation
    prep = InterviewPreparationSession(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Mock Backend Round",
    )
    db_session.add(prep)
    db_session.flush()

    q = InterviewQuestion(
        id=uuid.uuid4(),
        session_id=prep.id,
        question_text="Explain database connection pooling.",
        category="system_design",
        difficulty="intermediate",
        question_order=1,
    )
    db_session.add(q)
    db_session.flush()

    ans = InterviewAnswer(
        id=uuid.uuid4(),
        session_id=prep.id,
        question_id=q.id,
        user_id=user.id,
        answer_text="Connection pooling maintains reusable database connections.",
    )
    db_session.add(ans)
    db_session.flush()

    eval_record = InterviewEvaluation(
        id=uuid.uuid4(),
        session_id=prep.id,
        answer_id=ans.id,
        provider="gemini",
        model="gemini-1.5-flash",
        overall_score=85.0,
        technical_correctness_score=90.0,
        relevance_score=85.0,
        completeness_score=80.0,
        clarity_score=85.0,
        approach_score=85.0,
        communication_score=85.0,
        stronger_answer_example="Explain pool size tuning and leak detection.",
        evaluation_feedback="Comprehensive explanation of database connection pooling.",
    )
    db_session.add(eval_record)
    db_session.commit()

    res = client.get("/api/v1/career-command-center/readiness", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["readiness_score"] > 0.0
    assert "readiness score" in data["readiness_score_formula"].lower()
    assert (
        "limitations" in data["score_limitations"].lower()
        or "readiness score" in data["score_limitations"].lower()
    )

    # Check demonstrated skills
    demo_skills = [s["skill"] for s in data["demonstrated_skills"]]
    assert "Python" in demo_skills
    assert "FastAPI" in demo_skills

    # Check market demand skills
    req_skills = {s["skill"]: s for s in data["frequently_requested_skills"]}
    assert "Python" in req_skills
    assert req_skills["Python"]["is_demonstrated_by_user"] is True
    if "Kubernetes" in req_skills:
        assert req_skills["Kubernetes"]["is_demonstrated_by_user"] is False

    # Check missing skills includes Kubernetes
    gap_skills = [g["skill"] for g in data["missing_or_underrepresented_skills"]]
    assert "Kubernetes" in gap_skills

    # Check interview performance
    interview_perf = data["interview_performance"]
    assert interview_perf["completed_sessions_count"] == 1
    assert interview_perf["average_overall_score"] == 85.0
    assert len(interview_perf["top_strengths"]) > 0


def test_recommended_next_actions_prioritization(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "actions_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    # Setup: Application in interview status without interview prep
    app = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="interview",
        submission_confirmed=True,
    )
    db_session.add(app)

    # Setup: Application preparation incomplete
    prep = ApplicationPreparation(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        checklist_status="in_progress",
    )
    db_session.add(prep)
    db_session.commit()

    res = client.get("/api/v1/career-command-center/recommendations", headers=headers)
    assert res.status_code == 200
    data = res.json()

    actions = data["actions"]
    assert len(actions) >= 2

    action_types = [a["action_type"] for a in actions]
    assert "prepare_interview" in action_types
    assert "complete_prep" in action_types

    # Verify high priority item comes first
    assert actions[0]["priority"] == "high"
    assert actions[0]["navigation_url"] != ""


def test_performance_analytics_with_statistical_safeguards(client: TestClient, db_session: Session):
    headers, email = create_user_and_auth(client, "analytics_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    # Add 2 applications (sample size < 5)
    app1 = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="applied",
        submission_confirmed=True,
    )
    app2 = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="interview",
        submission_confirmed=True,
    )
    db_session.add_all([app1, app2])
    db_session.commit()

    res = client.get("/api/v1/career-command-center/analytics?date_range=all", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert len(data["weekly_activity"]) > 0
    assert len(data["monthly_activity"]) > 0
    assert data["interview_sample_size"] == 2
    # Statistical safeguard: sample size < 5 should not be considered statistically meaningful
    assert data["is_interview_sample_meaningful"] is False
    assert data["is_offer_sample_meaningful"] is False

    assert len(data["applications_by_role_family"]) > 0
    assert len(data["applications_by_company_category"]) > 0
    assert data["saved_vs_applied"]["applied_count"] == 2


def test_career_goals_read_and_update(client: TestClient, db_session: Session):
    headers, _ = create_user_and_auth(client, "goals_user@example.com")

    # 1. Read default goals
    get_res = client.get("/api/v1/career-command-center/goals", headers=headers)
    assert get_res.status_code == 200
    initial = get_res.json()
    assert initial["weekly_application_target"] == 5

    # 2. Update goals
    update_payload = {
        "target_role_families": ["backend_engineer", "fullstack_engineer"],
        "preferred_locations": ["Bengaluru", "Remote"],
        "work_arrangement_preferences": ["remote", "hybrid"],
        "min_salary": 1500000.0,
        "salary_currency": "INR",
        "salary_period": "annual",
        "preferred_company_categories": ["product", "startup"],
        "priority_technical_skills": ["Python", "FastAPI", "Kubernetes"],
        "weekly_application_target": 8,
    }
    put_res = client.put(
        "/api/v1/career-command-center/goals",
        json=update_payload,
        headers=headers,
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["weekly_application_target"] == 8
    assert updated["target_role_families"] == ["backend_engineer", "fullstack_engineer"]
    assert updated["min_salary"] == 1500000.0
    assert "Kubernetes" in updated["priority_technical_skills"]

    # 3. Verify overview reflects updated weekly target
    ov_res = client.get("/api/v1/career-command-center/overview", headers=headers)
    assert ov_res.json()["weekly_application_target"] == 8


def test_cross_user_data_isolation(client: TestClient, db_session: Session):
    headers_a, email_a = create_user_and_auth(client, "user_alpha@example.com")
    headers_b, email_b = create_user_and_auth(client, "user_beta@example.com")

    user_a, company, job, resume, version = setup_command_center_data(db_session, email_a)

    # User A creates application and sets goal
    app_a = JobApplication(
        id=uuid.uuid4(),
        user_id=user_a.id,
        job_id=job.id,
        company_id=company.id,
        title=job.title,
        company_name=company.name,
        status="offer",
        submission_confirmed=True,
    )
    db_session.add(app_a)
    db_session.commit()

    client.put(
        "/api/v1/career-command-center/goals",
        json={"weekly_application_target": 12},
        headers=headers_a,
    )

    # User B should see 0 offers and default weekly target
    res_b = client.get("/api/v1/career-command-center/overview", headers=headers_b)
    data_b = res_b.json()
    assert data_b["offers_received"] == 0
    assert data_b["weekly_application_target"] == 5

    funnel_b = client.get("/api/v1/career-command-center/funnel", headers=headers_b).json()
    assert funnel_b["outcomes"]["offered"] == 0


def test_api_authentication_required(client: TestClient):
    # Unauthenticated requests must fail with 401
    endpoints = [
        "/api/v1/career-command-center/overview",
        "/api/v1/career-command-center/funnel",
        "/api/v1/career-command-center/readiness",
        "/api/v1/career-command-center/recommendations",
        "/api/v1/career-command-center/analytics",
        "/api/v1/career-command-center/goals",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code in (401, 403)


def test_career_overview_and_analytics_date_range_filtering(
    client: TestClient, db_session: Session
):
    headers, email = create_user_and_auth(client, "daterange_user@example.com")
    user, company, job, resume, version = setup_command_center_data(db_session, email)

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=60)
    recent_time = now - timedelta(days=5)

    # Old application (60 days ago)
    app_old = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title="Old Application",
        company_name=company.name,
        status="applied",
        submission_confirmed=True,
        applied_at=old_time,
        created_at=old_time,
    )
    # Recent application (5 days ago)
    app_recent = JobApplication(
        id=uuid.uuid4(),
        user_id=user.id,
        job_id=job.id,
        company_id=company.id,
        title="Recent Application",
        company_name=company.name,
        status="applied",
        submission_confirmed=True,
        applied_at=recent_time,
        created_at=recent_time,
    )
    db_session.add_all([app_old, app_recent])
    db_session.commit()

    # 30-day filter: should only capture recent application
    res_30d = client.get("/api/v1/career-command-center/overview?date_range=30d", headers=headers)
    assert res_30d.status_code == 200
    assert res_30d.json()["applications_submitted"] == 1

    # 90-day filter: should capture both applications
    res_90d = client.get("/api/v1/career-command-center/overview?date_range=90d", headers=headers)
    assert res_90d.status_code == 200
    assert res_90d.json()["applications_submitted"] == 2

    # All filter: should capture both applications
    res_all = client.get("/api/v1/career-command-center/overview?date_range=all", headers=headers)
    assert res_all.status_code == 200
    assert res_all.json()["applications_submitted"] == 2
