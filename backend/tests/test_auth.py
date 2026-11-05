from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.models.token import RefreshToken


def test_password_hashing_and_verification() -> None:
    raw = "MyP@ssw0rd!2026"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongP@ssw0rd!1", hashed) is False


def test_password_strength_validation() -> None:
    # Valid password
    validate_password_strength("ValidP@ssw0rd1")

    # Too short
    with pytest.raises(Exception, match="at least 8 characters"):
        validate_password_strength("P@s1")

    # Missing uppercase
    with pytest.raises(Exception, match="uppercase letter"):
        validate_password_strength("validp@ssw0rd1")

    # Missing lowercase
    with pytest.raises(Exception, match="lowercase letter"):
        validate_password_strength("VALIDP@SSW0RD1")

    # Missing digit
    with pytest.raises(Exception, match="digit"):
        validate_password_strength("ValidP@ssword!")

    # Missing special char
    with pytest.raises(Exception, match="special character"):
        validate_password_strength("ValidPassword123")


def test_registration_success(client: TestClient) -> None:
    payload = {
        "email": "NewUser@Example.COM",
        "password": "StrongPassword123!",
        "full_name": "New User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data

    # Verify cookie was set
    assert "refresh_token" in response.cookies


def test_registration_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
        "full_name": "First User",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email (case insensitive)
    res2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUPLICATE@example.com",
            "password": "AnotherPassword456!",
            "full_name": "Second User",
        },
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "CONFLICT"


def test_login_success(client: TestClient) -> None:
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "Login User",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "refresh_token" in response.cookies


def test_login_generic_failure_messages(client: TestClient) -> None:
    # Non-existent email
    res1 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "StrongPassword123!"},
    )
    assert res1.status_code == 401
    assert res1.json()["error"]["message"] == "Invalid email or password"

    # Existing email with wrong password
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "realuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "Real User",
        },
    )
    res2 = client.post(
        "/api/v1/auth/login",
        json={"email": "realuser@example.com", "password": "WrongPassword123!"},
    )
    assert res2.status_code == 401
    assert res2.json()["error"]["message"] == "Invalid email or password"


def test_access_token_and_users_me(client: TestClient) -> None:
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "me_user@example.com",
            "password": "StrongPassword123!",
            "full_name": "Me User",
        },
    )
    token = reg_res.json()["access_token"]

    # Request /users/me with valid Bearer token
    me_res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "me_user@example.com"
    assert user_data["full_name"] == "Me User"
    assert user_data["is_active"] is True
    # Ensure sensitive fields are NEVER returned
    assert "hashed_password" not in user_data
    assert "password" not in user_data


def test_users_me_unauthorized_missing_token(client: TestClient) -> None:
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_users_me_expired_token(client: TestClient) -> None:
    # Generate expired token
    expired_token = create_access_token(
        subject="00000000-0000-0000-0000-000000000000",
        expires_delta=timedelta(seconds=-10),
    )
    res = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_refresh_token_rotation_and_revocation(client: TestClient, db_session: Session) -> None:
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh_user@example.com",
            "password": "StrongPassword123!",
            "full_name": "Refresh User",
        },
    )
    initial_refresh = reg_res.json()["refresh_token"]

    # Perform refresh using payload
    ref_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert "access_token" in new_tokens
    new_refresh = new_tokens["refresh_token"]
    assert new_refresh != initial_refresh

    # Verify old refresh token is now revoked in database
    old_hash = hash_token(initial_refresh)
    old_record = db_session.query(RefreshToken).filter(RefreshToken.token_hash == old_hash).first()
    assert old_record is not None
    assert old_record.revoked_at is not None

    # Attempting to reuse revoked initial_refresh should fail (rotation protection)
    reuse_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert reuse_res.status_code == 401
    assert reuse_res.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout(client: TestClient, db_session: Session) -> None:
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout_user@example.com",
            "password": "StrongPassword123!",
            "full_name": "Logout User",
        },
    )
    refresh_token = reg_res.json()["refresh_token"]

    logout_res = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out"

    # Verify token is marked revoked
    token_hash = hash_token(refresh_token)
    record = db_session.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    assert record is not None
    assert record.revoked_at is not None


def test_audit_event_emitted_without_secrets() -> None:
    mock_sink = MagicMock()
    with patch.object(audit_service, "_sink", mock_sink):
        event = audit_service.record_event(
            action="auth.login",
            resource_type="user",
            actor_type="user",
            actor_id="user_test_id",
            metadata={
                "email": "user@example.com",
                "password": "SensitivePassword123!",
                "token": "secret_jwt_token",
            },
        )
        assert event.metadata["email"] == "user@example.com"
        assert event.metadata["password"] == "[REDACTED]"
        assert event.metadata["token"] == "[REDACTED]"
        mock_sink.emit.assert_called_once()
