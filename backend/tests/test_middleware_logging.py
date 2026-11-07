from fastapi.testclient import TestClient

from app.core.logging import sanitize_data


def test_request_id_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_request_id_propagated_when_valid(client: TestClient) -> None:
    custom_id = "custom-trace-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_request_id_replaced_when_invalid(client: TestClient) -> None:
    invalid_id = "invalid id with spaces &!@#"
    response = client.get("/health", headers={"X-Request-ID": invalid_id})
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert req_id != invalid_id


def test_sanitize_data_redacts_sensitive_keys() -> None:
    payload = {
        "user": "test_user",
        "password": "super_secret_password",
        "api_key": "123456",
        "nested": {
            "token": "bearer_xyz",
            "normal": "value",
        },
        "items": [
            {"access_token": "secret_abc"},
            {"item_name": "resume.pdf"},
        ],
    }
    cleaned = sanitize_data(payload)
    assert cleaned["user"] == "test_user"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["token"] == "[REDACTED]"
    assert cleaned["nested"]["normal"] == "value"
    assert cleaned["items"][0]["access_token"] == "[REDACTED]"
    assert cleaned["items"][1]["item_name"] == "resume.pdf"


def test_security_headers_present_on_all_responses(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")
