import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError
from app.models.company import Company
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.services.latex_compiler import (
    compile_resume_to_pdf,
    validate_latex_security,
)
from app.services.latex_generator import escape_latex, generate_latex_resume
from app.services.tailoring_analyzer import TailoringAnalyzer
from app.services.tailoring_engine import TailoringEngine


def sample_parsed_resume() -> dict[str, Any]:
    return {
        "contact": {
            "name": "Jane Developer",
            "email": "jane@example.com",
            "phone": "+1-555-0199",
            "location": "San Francisco, CA",
            "links": ["https://github.com/janedev"],
        },
        "summary": "Motivated software engineer with experience in Python and PostgreSQL.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        "experience": [
            {
                "title": "Junior Backend Engineer",
                "company": "Startup Co",
                "date_range": "2023 - Present",
                "bullets": [
                    "Developed RESTful API endpoints using FastAPI and PostgreSQL.",
                    "Implemented unit test suites with pytest to achieve 85% coverage.",
                ],
            }
        ],
        "projects": [
            {
                "title": "Task Orchestrator",
                "bullets": [
                    "Built an asynchronous job queue using Python and Redis.",
                ],
            }
        ],
        "education": [
            {
                "institution": "University of Technology",
                "degree": "B.S. in Computer Science",
                "year": "2023",
                "details": ["Dean's Honor List"],
            }
        ],
    }


def create_user_and_token(
    client: TestClient,
    email: str = "tailor_user@example.com",
) -> tuple[dict[str, str], str]:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Jane Tailor",
    }
    client.post("/api/v1/auth/register", json=payload)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def setup_test_entities(db: Session, user_email: str) -> tuple[User, Resume, ResumeVersion, Job]:
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        from app.core.security import hash_password

        user = User(
            id=uuid.uuid4(),
            email=user_email,
            hashed_password=hash_password("SecurePassword123!"),
            full_name="Jane Tailor",
            is_active=True,
        )
        db.add(user)
        db.flush()

    company = Company(
        id=uuid.uuid4(),
        name="Apex Cloud Systems",
        normalized_name="apex cloud systems",
        website_url="https://apexcloud.example",
        normalized_domain="apexcloud.example",
        category="product_company",
    )
    db.add(company)
    db.flush()

    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Backend Software Engineer",
        normalized_title="backend software engineer",
        description="Looking for early-career backend engineers proficient in Python and FastAPI. "
        "Knowledge of AWS, Docker, and PostgreSQL is desired.",
        skills_tags=["Python", "FastAPI", "PostgreSQL", "AWS"],
        seniority_level="entry_level",
        work_arrangement="remote",
        job_url="https://apexcloud.example/jobs/1",
        verification_status="verified",
    )
    db.add(job)

    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Software Engineering Resume",
    )
    db.add(resume)
    db.flush()

    parsed = sample_parsed_resume()
    version = ResumeVersion(
        id=uuid.uuid4(),
        resume_id=resume.id,
        version_number=1,
        original_filename="jane_dev.pdf",
        file_type="pdf",
        file_size=10240,
        storage_path=f"storage/resumes/{user.id}/{resume.id}/v1/jane_dev.pdf",
        parsing_status="parsed",
        parsed_content=parsed,
        raw_text="Jane Developer software engineer Python FastAPI PostgreSQL Docker",
    )
    db.add(version)
    resume.current_version_id = version.id
    db.commit()

    return user, resume, version, job


# --- Unit Tests ---


def test_escape_latex() -> None:
    raw = "Proficient in C++ & Python (100% test coverage) with $50k cost savings #1"
    escaped = escape_latex(raw)
    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\$" in escaped
    assert r"\#" in escaped


def test_latex_generator_structure() -> None:
    parsed = sample_parsed_resume()
    latex = generate_latex_resume(
        parsed,
        job_title="Backend Engineer",
        company_name="Apex Cloud",
    )
    assert r"\documentclass" in latex
    assert "Jane Developer" in latex
    assert "Backend Engineer" in latex
    assert "Apex Cloud" in latex
    assert "FastAPI" in latex
    assert r"\end{document}" in latex


def test_latex_security_sandboxing() -> None:
    # Safe LaTeX
    clean_tex = r"\documentclass{article}\begin{document}Hello world\end{document}"
    validate_latex_security(clean_tex)  # should not raise

    # Prohibited commands
    dangerous_commands = [
        r"\write18{rm -rf /}",
        r"\input{/etc/passwd}",
        r"\sys_exec{cat /etc/shadow}",
        r"\openin 1=/etc/hosts",
        r"\newwrite\testfile",
    ]
    for cmd in dangerous_commands:
        with pytest.raises(BadRequestError) as exc_info:
            validate_latex_security(cmd)
        assert "Security violation" in str(exc_info.value)


def test_tailoring_analyzer_zero_fabrication(db_session: Session) -> None:
    _, _, version, job = setup_test_entities(db_session, "tailor_user@example.com")
    analysis = TailoringAnalyzer.analyze_requirements(job, version)

    # Candidate has Python, FastAPI, PostgreSQL
    assert "Python" in analysis.relevant_skills
    assert "FastAPI" in analysis.relevant_skills
    assert "PostgreSQL" in analysis.relevant_skills

    # Candidate does NOT have AWS -> must be in missing_requirements
    assert "AWS" in analysis.missing_requirements
    # Critical Zero-Fabrication assertion: missing skill must never be claimed in relevant skills
    assert "AWS" not in analysis.relevant_skills


def test_tailoring_engine_traceability(db_session: Session) -> None:
    _, _, version, job = setup_test_entities(db_session, "tailor_user@example.com")
    analysis = TailoringAnalyzer.analyze_requirements(job, version)

    changes, provider, model = TailoringEngine.generate_changes(job, version, analysis)
    assert len(changes) > 0
    assert provider is not None

    for change in changes:
        assert change.supporting_evidence is not None
        assert "section" in change.supporting_evidence
        assert "excerpt" in change.supporting_evidence
        assert change.change_type in (
            "wording_improvement",
            "restructuring",
            "relevance_improvement",
            "keyword_alignment",
        )
        assert change.confidence_level in ("high", "medium", "low")


def test_pdf_compilation_fallback() -> None:
    parsed = sample_parsed_resume()
    clean_tex = generate_latex_resume(parsed, job_title="Engineer", company_name="Co")
    pdf_bytes, page_count, engine = compile_resume_to_pdf(clean_tex, parsed_fallback=parsed)
    assert len(pdf_bytes) > 0
    assert page_count >= 1
    assert pdf_bytes.startswith(b"%PDF")
    assert engine in ("pdflatex", "structured_layout_renderer")


# --- API Integration Tests ---


def test_tailoring_session_lifecycle(client: TestClient, db_session: Session) -> None:
    headers, email = create_user_and_token(client, "lifecycle@example.com")
    user, resume, version, job = setup_test_entities(db_session, email)

    # 1. Create Session
    create_payload = {
        "resume_id": str(resume.id),
        "version_id": str(version.id),
        "job_id": str(job.id),
    }
    resp = client.post("/api/v1/tailoring/sessions", json=create_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    session_data = resp.json()
    session_id = session_data["id"]
    assert session_data["status"] == "ready"
    assert len(session_data["changes"]) > 0
    assert session_data["job"]["title"] == "Backend Software Engineer"
    assert "Apex Cloud Systems" in session_data["latex_content"]

    # 2. List Sessions
    list_resp = client.get("/api/v1/tailoring/sessions", headers=headers)
    assert list_resp.status_code == 200
    summaries = list_resp.json()
    assert len(summaries) >= 1
    assert any(s["id"] == session_id for s in summaries)

    # 3. Get Session
    get_resp = client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

    # 4. Update Single Change Status (Accept)
    first_change = session_data["changes"][0]
    change_id = first_change["id"]
    patch_resp = client.patch(
        f"/api/v1/tailoring/sessions/{session_id}/changes/{change_id}",
        json={"status": "accepted"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    updated_changes = patch_resp.json()["changes"]
    target_c = next(c for c in updated_changes if c["id"] == change_id)
    assert target_c["status"] == "accepted"

    # 5. Modify Change with Custom User Content
    patch_mod = client.patch(
        f"/api/v1/tailoring/sessions/{session_id}/changes/{change_id}",
        json={
            "status": "modified",
            "user_content": "Engineered high-throughput FastAPI services with PostgreSQL.",
        },
        headers=headers,
    )
    assert patch_mod.status_code == 200
    mod_c = next(c for c in patch_mod.json()["changes"] if c["id"] == change_id)
    assert mod_c["status"] == "modified"
    assert mod_c["active_content"] == (
        "Engineered high-throughput FastAPI services with PostgreSQL."
    )

    # 6. Batch Action: Accept All
    batch_resp = client.post(
        f"/api/v1/tailoring/sessions/{session_id}/batch",
        json={"action": "accept_all"},
        headers=headers,
    )
    assert batch_resp.status_code == 200
    all_accepted = all(
        c["status"] in ("accepted", "modified") for c in batch_resp.json()["changes"]
    )
    assert all_accepted

    # 7. Update Monaco LaTeX Content
    valid_latex = patch_mod.json()["latex_content"] + "\n% Editor comment"
    put_resp = client.put(
        f"/api/v1/tailoring/sessions/{session_id}/content",
        json={"latex_content": valid_latex},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert "% Editor comment" in put_resp.json()["latex_content"]

    # 8. Malicious LaTeX in Monaco Editor Rejected
    bad_latex = valid_latex + r"\n\write18{whoami}"
    bad_resp = client.put(
        f"/api/v1/tailoring/sessions/{session_id}/content",
        json={"latex_content": bad_latex},
        headers=headers,
    )
    assert bad_resp.status_code == 400
    assert "Security violation" in str(bad_resp.json())

    # 9. Compile PDF Endpoint
    compile_resp = client.post(
        f"/api/v1/tailoring/sessions/{session_id}/compile",
        json={},
        headers=headers,
    )
    assert compile_resp.status_code == 200
    assert compile_resp.json()["success"] is True

    # 10. Download PDF Endpoint
    pdf_stream = client.get(f"/api/v1/tailoring/sessions/{session_id}/pdf", headers=headers)
    assert pdf_stream.status_code == 200
    assert pdf_stream.headers["Content-Type"] == "application/pdf"
    assert pdf_stream.content.startswith(b"%PDF")

    # 11. Download TeX Source Endpoint
    tex_stream = client.get(f"/api/v1/tailoring/sessions/{session_id}/latex", headers=headers)
    assert tex_stream.status_code == 200
    assert "text/x-tex" in tex_stream.headers["Content-Type"]
    assert "documentclass" in tex_stream.text

    # 12. Save Tailored Resume as Immutable Version
    save_resp = client.post(
        f"/api/v1/tailoring/sessions/{session_id}/save",
        json={"title": "Tailored Backend Resume - Apex Cloud"},
        headers=headers,
    )
    assert save_resp.status_code == 201
    tailored_version_data = save_resp.json()
    assert tailored_version_data["is_tailored"] is True
    assert tailored_version_data["parent_version_id"] == str(version.id)
    assert tailored_version_data["job_id"] == str(job.id)
    assert tailored_version_data["version_number"] == 2

    # Verify original version in DB was NOT altered (immutability check)
    db_session.expire_all()
    orig_version = db_session.get(ResumeVersion, version.id)
    assert orig_version is not None
    assert orig_version.version_number == 1
    assert orig_version.is_tailored is False
    assert orig_version.parent_version_id is None


def test_tailoring_user_isolation(client: TestClient, db_session: Session) -> None:
    headers_a, email_a = create_user_and_token(client, "user_a@example.com")
    headers_b, email_b = create_user_and_token(client, "user_b@example.com")

    _, resume_a, version_a, job = setup_test_entities(db_session, email_a)

    # User A creates a session
    resp = client.post(
        "/api/v1/tailoring/sessions",
        json={
            "resume_id": str(resume_a.id),
            "version_id": str(version_a.id),
            "job_id": str(job.id),
        },
        headers=headers_a,
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # User B cannot access User A's session
    resp_b = client.get(f"/api/v1/tailoring/sessions/{session_id}", headers=headers_b)
    assert resp_b.status_code == 404
