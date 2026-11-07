import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequestError
from app.core.oauth_state import generate_oauth_state, verify_oauth_state
from app.core.security import create_access_token, hash_password, verify_password
from app.core.storage import LocalStorageService, StorageError
from app.models.ai_usage import AIUsageLog
from app.models.user import User
from app.services.ai.cost_manager import AICostManager


def _create_test_user(db: Session, email: str, name: str) -> tuple[User, dict[str, str]]:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("ComplexP@ssw0rd!2026"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    token = create_access_token(subject=str(user.id))
    return user, {"Authorization": f"Bearer {token}"}


def test_sql_injection_resilience(client: TestClient, db_session: Session) -> None:
    """Verify that SQL injection payloads in query parameters do not cause errors or leaks."""
    user, headers = _create_test_user(db_session, "sqli_test@example.com", "SQLi Tester")

    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT id, email, hashed_password FROM users --",
        "1' ORDER BY 1--+",
        "admin'--",
    ]

    for payload in sql_payloads:
        # Search jobs
        job_res = client.get(f"/api/v1/jobs?search={payload}", headers=headers)
        assert job_res.status_code == 200, f"Jobs search failed on payload: {payload}"

        # Search recruiters
        rec_res = client.get(f"/api/v1/networking/recruiters?query={payload}", headers=headers)
        assert rec_res.status_code == 200, f"Recruiters query failed on payload: {payload}"

        # Applications search/status filter
        app_res = client.get(f"/api/v1/applications?status={payload}", headers=headers)
        assert app_res.status_code in (200, 422), f"Applications query failed on payload: {payload}"


def test_xss_and_html_injection_handling(client: TestClient, db_session: Session) -> None:
    """Verify that stored XSS payloads in profile fields are treated strictly as text data."""
    user, headers = _create_test_user(db_session, "xss_tester@example.com", "XSS Tester")

    xss_payload = "<script>alert('XSS_EXEC')</script><img src=x onerror=alert(1)>"

    # Initialize portfolio
    init_res = client.get("/api/v1/portfolios/me", headers=headers)
    assert init_res.status_code == 200

    # Update portfolio profile with XSS in headline
    port_res = client.put(
        "/api/v1/portfolios/profile",
        json={
            "headline": f"Dev {xss_payload}",
            "profile_data": {"summary": f"Engineer with {xss_payload}"},
        },
        headers=headers,
    )
    assert port_res.status_code == 200
    port_data = port_res.json()

    # The payload is safely stored and serialized as JSON string, never executed
    assert port_data["headline"] == f"Dev {xss_payload}"

    # Verify retrieval
    get_res = client.get("/api/v1/portfolios/me", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["headline"] == f"Dev {xss_payload}"
    assert get_res.headers["content-type"].startswith("application/json")


def test_storage_path_traversal_prevention(tmp_path: Path) -> None:
    """Verify that LocalStorageService rejects directory traversal attempts."""
    storage = LocalStorageService(base_path=str(tmp_path))

    traversal_paths = [
        "../../etc/passwd",
        "../secrets.env",
        "/etc/shadow",
        "user/../../../../var/log/system.log",
        "a/b/../../../../../../etc/passwd",
    ]

    for malicious_path in traversal_paths:
        with pytest.raises(StorageError):
            storage._resolve_safe_path(malicious_path)

        with pytest.raises(StorageError):
            storage.get_file(malicious_path)

        with pytest.raises(StorageError):
            storage.delete_file(malicious_path)


def test_file_upload_security_validation(client: TestClient, db_session: Session) -> None:
    """Verify that file uploads enforce MIME, extension, magic byte, and size restrictions."""
    user, headers = _create_test_user(db_session, "uploader_sec@example.com", "Upload Sec")

    # 1. Disallowed file extensions (e.g. .exe, .sh, .py, .html)
    malicious_files = [
        ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload"),
        ("exploit.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
        ("phish.html", b"<html><body>Phishing</body></html>", "text/html"),
    ]

    for fname, content, ctype in malicious_files:
        res = client.post(
            "/api/v1/resumes",
            files={"file": (fname, io.BytesIO(content), ctype)},
            headers=headers,
        )
        assert res.status_code in (400, 422), f"Should reject unsupported file {fname}"

    # 2. Spoofed extension: filename is .pdf, but content is text/plain
    spoofed_res = client.post(
        "/api/v1/resumes",
        files={
            "file": ("fake.pdf", io.BytesIO(b"Hello world this is not a PDF"), "application/pdf")
        },
        headers=headers,
    )
    assert spoofed_res.status_code == 400
    assert "PDF header" in spoofed_res.json()["error"]["message"]

    # 3. Oversize file > MAX_UPLOAD_SIZE_BYTES (e.g. limit is 10MB)
    oversize_bytes = b"%PDF-1.4\n" + (b"0" * (settings.MAX_UPLOAD_SIZE_BYTES + 1024))
    oversize_res = client.post(
        "/api/v1/resumes",
        files={"file": ("huge.pdf", io.BytesIO(oversize_bytes), "application/pdf")},
        headers=headers,
    )
    assert oversize_res.status_code == 400
    assert "exceeds maximum allowed limit" in oversize_res.json()["error"]["message"]


def test_ai_budget_and_limit_enforcement(db_session: Session) -> None:
    """Verify that AICostManager strictly enforces platform budgets and user limits."""
    user, _ = _create_test_user(db_session, "budget_sec@example.com", "Budget Sec")

    # Under budget should be allowed
    check_ok = AICostManager.check_limits_and_cache(db=db_session, user_id=user.id)
    assert check_ok.allowed is True

    # Seed an artificial log that exceeds platform daily budget
    over_log = AIUsageLog(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="openai",
        model="gpt-4o",
        feature="orchestration",
        prompt_tokens=100000,
        completion_tokens=50000,
        total_tokens=150000,
        estimated_cost_usd=settings.AI_DAILY_BUDGET_USD + 5.0,
        request_status="completed",
    )
    db_session.add(over_log)
    db_session.commit()

    # Re-check limits: must now be blocked
    check_blocked = AICostManager.check_limits_and_cache(db=db_session, user_id=user.id)
    assert check_blocked.allowed is False
    assert "daily AI spending limit exceeded" in check_blocked.reason


def test_oauth_state_signature_and_csrf_protection(db_session: Session) -> None:
    """Verify tamper-evident HMAC signing, user-binding, and expiry of OAuth states."""
    user1, _ = _create_test_user(db_session, "oauth1@example.com", "OAuth User 1")
    user2, _ = _create_test_user(db_session, "oauth2@example.com", "OAuth User 2")

    state = generate_oauth_state(user_id=user1.id, action="gmail_connect")
    assert "." in state

    # 1. Valid state verification succeeds
    verified = verify_oauth_state(
        state=state, expected_user_id=user1.id, expected_action="gmail_connect"
    )
    assert verified["uid"] == str(user1.id)
    assert verified["act"] == "gmail_connect"

    # 2. Tampered signature fails
    payload_b64, sig = state.split(".", 1)
    tampered_state = f"{payload_b64}.tamperedsignature12345"
    with pytest.raises(BadRequestError, match="invalid signature"):
        verify_oauth_state(
            state=tampered_state, expected_user_id=user1.id, expected_action="gmail_connect"
        )

    # 3. Wrong user attempt fails (cross-user replay)
    with pytest.raises(BadRequestError, match="OAuth state user mismatch"):
        verify_oauth_state(state=state, expected_user_id=user2.id, expected_action="gmail_connect")

    # 4. Wrong action attempt fails
    with pytest.raises(BadRequestError, match="OAuth state action mismatch"):
        verify_oauth_state(
            state=state, expected_user_id=user1.id, expected_action="calendar_connect"
        )

    # 5. Expired state fails
    with pytest.raises(BadRequestError, match="OAuth state has expired"):
        verify_oauth_state(
            state=state,
            expected_user_id=user1.id,
            expected_action="gmail_connect",
            max_age_seconds=-1,
        )


def test_password_hashing_and_security() -> None:
    """Verify strong hashing with bcrypt salt generation and verification."""
    password = "MyStrongSecurePassword!123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
