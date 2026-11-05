from unittest.mock import patch

from fastapi.testclient import TestClient


def test_root_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


def test_api_v1_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


def test_health_endpoints_do_not_call_database(client: TestClient) -> None:
    """Verify healthchecks remain fast and decouple from database connectivity."""
    with patch("app.core.database.SessionLocal") as mock_sessionmaker:
        resp1 = client.get("/health")
        resp2 = client.get("/api/v1/health")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        mock_sessionmaker.assert_not_called()
