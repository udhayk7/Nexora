import io
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import docx
import pytest
from fastapi.testclient import TestClient

from app.core.audit import audit_service
from app.core.config import settings
from app.core.storage import storage_service
from app.services.resume_parser import resume_parser

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[Any] = []

    def emit(self, event: Any) -> None:
        self.events.append(event)


def generate_sample_docx(
    name: str = "Jane Developer",
    email: str = "jane.dev@example.com",
    phone: str = "555-432-1098",
    skills: str = "Python, FastAPI, TypeScript, React, Docker, PostgreSQL",
) -> bytes:
    doc = docx.Document()
    doc.add_heading(name, level=1)
    doc.add_paragraph(f"{email} | {phone} | linkedin.com/in/janedev")

    doc.add_heading("Professional Summary", level=2)
    doc.add_paragraph("Full-stack engineer with 6 years experience building scalable web apps.")

    doc.add_heading("Technical Skills", level=2)
    doc.add_paragraph(skills)

    doc.add_heading("Work Experience", level=2)
    doc.add_paragraph("Senior Engineer at NexaCorp - Jan 2021 to Present")
    doc.add_paragraph("• Architected low-latency distributed APIs")
    doc.add_paragraph("• Led migration from monolith to microservices")

    doc.add_heading("Education", level=2)
    doc.add_paragraph("Bachelor of Science in Computer Science - 2019")
    doc.add_paragraph("State University")

    doc.add_heading("Certifications", level=2)
    doc.add_paragraph("AWS Certified Solutions Architect")

    doc.add_heading("Key Projects", level=2)
    doc.add_paragraph("High-throughput telemetry ingestion pipeline")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_sample_pdf(text: str = "Jane Developer\njane.dev@example.com\n555-432-1098") -> bytes:
    # Minimal valid PDF with text stream
    content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    pdf_str = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(content)} >>
stream
{content}
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000340 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
425
%%EOF"""
    return pdf_str.encode("latin-1")


@pytest.fixture
def auth_headers_user1(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "password": "Password123!", "full_name": "User One"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user2(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "user2@example.com", "password": "Password123!", "full_name": "User Two"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Generator[None, None, None]:
    original_base = storage_service.base_dir
    storage_service.base_dir = tmp_path
    yield
    storage_service.base_dir = original_base


# 1. Deterministic Resume Parser Unit Tests
def test_resume_parser_docx_success() -> None:
    docx_bytes = generate_sample_docx()
    raw_text, parsed_data, status, error = resume_parser.parse_document(docx_bytes, "docx")

    assert status == "parsed"
    assert error is None
    assert "Full-stack engineer" in raw_text
    assert parsed_data["contact"]["email"] == "jane.dev@example.com"
    assert parsed_data["contact"]["phone"] == "555-432-1098"
    assert "Python" in parsed_data["skills"]
    assert "FastAPI" in parsed_data["skills"]
    assert len(parsed_data["experience"]) >= 1
    assert "AWS Certified Solutions Architect" in parsed_data["certifications"]


def test_resume_parser_pdf_success() -> None:
    pdf_bytes = generate_sample_pdf("Alex Smith\nalex@example.com\n555-111-2222")
    raw_text, parsed_data, status, error = resume_parser.parse_document(pdf_bytes, "pdf")

    assert status == "parsed"
    assert error is None
    assert "alex@example.com" in raw_text
    assert parsed_data["contact"]["email"] == "alex@example.com"


def test_resume_parser_corrupted_or_empty() -> None:
    # Corrupted bytes claiming to be PDF
    raw_text, parsed_data, status, error = resume_parser.parse_document(
        b"%PDF corrupted junk", "pdf"
    )
    assert status == "failed"
    assert error is not None


# 2. Local Storage Tests
def test_storage_service_safe_save_and_retrieve(tmp_path: Path) -> None:
    uid = uuid.uuid4()
    rid = uuid.uuid4()
    vid = uuid.uuid4()
    content = b"test resume content"

    rel_path = storage_service.save_file(uid, rid, vid, "my_resume.pdf", content)
    assert str(uid) in rel_path
    assert str(rid) in rel_path

    retrieved = storage_service.get_file(rel_path)
    assert retrieved == content

    # Clean up
    deleted = storage_service.delete_file(rel_path)
    assert deleted is True

    with pytest.raises(FileNotFoundError):
        storage_service.get_file(rel_path)


# 3. API Upload & Validation Tests
def test_upload_resume_docx_success(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    docx_bytes = generate_sample_docx()
    files = {"file": ("my_resume.docx", docx_bytes, DOCX_MIME)}
    data = {"title": "Full Stack Resume 2026"}

    response = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files, data=data)
    assert response.status_code == 201

    body = response.json()
    assert body["title"] == "Full Stack Resume 2026"
    assert body["version_count"] == 1
    assert body["current_version"] is not None
    assert body["current_version"]["version_number"] == 1
    assert body["current_version"]["parsing_status"] == "parsed"
    assert body["current_version"]["parsed_content"]["contact"]["email"] == "jane.dev@example.com"


def test_upload_resume_pdf_success(client: TestClient, auth_headers_user1: dict[str, str]) -> None:
    pdf_bytes = generate_sample_pdf("Software Engineer\nengineer@example.com")
    files = {"file": ("engineer.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)
    assert response.status_code == 201

    body = response.json()
    assert body["title"] == "engineer"
    assert body["current_version"]["file_type"] == "pdf"


def test_upload_invalid_extension_rejected(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    files = {"file": ("malicious.exe", b"executable bytes", "application/octet-stream")}
    response = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert "Unsupported file type" in response.json()["error"]["message"]


def test_upload_mismatched_magic_bytes_rejected(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    # Has .pdf extension but content does not start with %PDF
    files = {"file": ("fake.pdf", b"plain text header instead of pdf", "application/pdf")}
    response = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)

    assert response.status_code == 400
    assert "File content does not match" in response.json()["error"]["message"]


def test_upload_oversized_file_rejected(
    client: TestClient, auth_headers_user1: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Set max size to 500 bytes for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 500)
    docx_bytes = generate_sample_docx()
    assert len(docx_bytes) > 500

    files = {"file": ("large.docx", docx_bytes, DOCX_MIME)}
    response = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)

    assert response.status_code == 400
    assert "File size exceeds" in response.json()["error"]["message"]


# 4. User Scoping & Isolation Tests
def test_user_isolation_list_and_details(
    client: TestClient, auth_headers_user1: dict[str, str], auth_headers_user2: dict[str, str]
) -> None:
    # User 1 uploads a resume
    docx_bytes = generate_sample_docx()
    files = {"file": ("user1_resume.docx", docx_bytes, DOCX_MIME)}
    res_upload = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)
    assert res_upload.status_code == 201
    user1_resume_id = res_upload.json()["id"]

    # User 1 lists resumes -> sees 1 resume
    res_list1 = client.get("/api/v1/resumes", headers=auth_headers_user1)
    assert res_list1.status_code == 200
    assert len(res_list1.json()) == 1
    assert res_list1.json()[0]["id"] == user1_resume_id

    # User 2 lists resumes -> sees 0 resumes
    res_list2 = client.get("/api/v1/resumes", headers=auth_headers_user2)
    assert res_list2.status_code == 200
    assert len(res_list2.json()) == 0

    # User 2 attempts to get User 1's resume details -> 404 (no existence leak)
    res_detail2 = client.get(f"/api/v1/resumes/{user1_resume_id}", headers=auth_headers_user2)
    assert res_detail2.status_code == 404
    assert res_detail2.json()["error"]["code"] == "NOT_FOUND"

    # User 2 attempts to download User 1's resume -> 404
    res_dl2 = client.get(f"/api/v1/resumes/{user1_resume_id}/download", headers=auth_headers_user2)
    assert res_dl2.status_code == 404

    # User 2 attempts to delete User 1's resume -> 404
    res_del2 = client.delete(f"/api/v1/resumes/{user1_resume_id}", headers=auth_headers_user2)
    assert res_del2.status_code == 404


# 5. Version Management Tests
def test_upload_new_version(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    # Upload version 1
    docx_bytes_v1 = generate_sample_docx(name="Jane V1", skills="Python, Django")
    files_v1 = {"file": ("v1.docx", docx_bytes_v1, DOCX_MIME)}
    res1 = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files_v1)
    assert res1.status_code == 201
    resume_id = res1.json()["id"]

    # Upload version 2
    docx_bytes_v2 = generate_sample_docx(name="Jane V2", skills="Python, FastAPI, Kubernetes")
    files_v2 = {"file": ("v2.docx", docx_bytes_v2, DOCX_MIME)}
    res2 = client.post(
        f"/api/v1/resumes/{resume_id}/versions", headers=auth_headers_user1, files=files_v2
    )
    assert res2.status_code == 201
    v2_body = res2.json()
    assert v2_body["version_number"] == 2
    assert "Kubernetes" in v2_body["parsed_content"]["skills"]

    # List versions
    res_versions = client.get(f"/api/v1/resumes/{resume_id}/versions", headers=auth_headers_user1)
    assert res_versions.status_code == 200
    versions = res_versions.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1

    # Resume detail should reflect version 2 as current
    res_detail = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers_user1)
    assert res_detail.status_code == 200
    assert res_detail.json()["version_count"] == 2
    assert res_detail.json()["current_version"]["version_number"] == 2


# 6. Download & Delete Tests
def test_download_and_delete_resume(
    client: TestClient, auth_headers_user1: dict[str, str]
) -> None:
    docx_bytes = generate_sample_docx()
    files = {"file": ("download_test.docx", docx_bytes, DOCX_MIME)}
    res = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)
    resume_id = res.json()["id"]
    version_id = res.json()["current_version"]["id"]

    # Download active version
    res_dl = client.get(f"/api/v1/resumes/{resume_id}/download", headers=auth_headers_user1)
    assert res_dl.status_code == 200
    assert res_dl.content == docx_bytes
    assert 'attachment; filename="download_test.docx"' in res_dl.headers["content-disposition"]

    # Download specific version
    res_dl_ver = client.get(
        f"/api/v1/resumes/{resume_id}/versions/{version_id}/download", headers=auth_headers_user1
    )
    assert res_dl_ver.status_code == 200
    assert res_dl_ver.content == docx_bytes

    # Delete resume
    res_del = client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers_user1)
    assert res_del.status_code == 204

    # Verify resume is gone
    res_gone = client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers_user1)
    assert res_gone.status_code == 404


# 7. Audit Logging Verification
def test_audit_events_emitted_during_resume_operations(
    client: TestClient, auth_headers_user1: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    sink = MemoryAuditSink()
    monkeypatch.setattr(audit_service, "_sink", sink)

    docx_bytes = generate_sample_docx()
    files = {"file": ("audit_test.docx", docx_bytes, DOCX_MIME)}
    res_upload = client.post("/api/v1/resumes", headers=auth_headers_user1, files=files)
    resume_id = res_upload.json()["id"]

    client.get(f"/api/v1/resumes/{resume_id}/download", headers=auth_headers_user1)
    client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers_user1)

    actions = [e.action for e in sink.events]
    assert "resume.upload" in actions
    assert "resume.parsed" in actions
    assert "resume.download" in actions
    assert "resume.delete" in actions
