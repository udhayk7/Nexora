from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.main import app

# Error test router for verifying exception handlers
error_test_router = APIRouter(prefix="/test-errors")


class DummyInput(BaseModel):
    name: str
    age: int


@error_test_router.get("/not-found")
def route_not_found() -> None:
    raise NotFoundError("Entity could not be located")


@error_test_router.get("/bad-request")
def route_bad_request() -> None:
    raise BadRequestError("Invalid parameter provided", details={"field": "query"})


@error_test_router.get("/forbidden")
def route_forbidden() -> None:
    raise ForbiddenError("Permission denied")


@error_test_router.get("/conflict")
def route_conflict() -> None:
    raise ConflictError("Resource already exists")


@error_test_router.get("/server-error")
def route_server_error() -> None:
    raise RuntimeError("Unexpected internal crash")


@error_test_router.post("/validation")
def route_validation(data: DummyInput) -> dict[str, str]:
    return {"status": "ok"}


app.include_router(error_test_router)


def test_not_found_error_format(client: TestClient) -> None:
    response = client.get("/test-errors/not-found")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Entity could not be located"
    assert "request_id" in data["error"]


def test_bad_request_error_format(client: TestClient) -> None:
    response = client.get("/test-errors/bad-request")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert data["error"]["details"] == {"field": "query"}


def test_forbidden_and_conflict_errors(client: TestClient) -> None:
    resp_forbidden = client.get("/test-errors/forbidden")
    assert resp_forbidden.status_code == 403
    assert resp_forbidden.json()["error"]["code"] == "FORBIDDEN"

    resp_conflict = client.get("/test-errors/conflict")
    assert resp_conflict.status_code == 409
    assert resp_conflict.json()["error"]["code"] == "CONFLICT"


def test_unhandled_route_404(client: TestClient) -> None:
    response = client.get("/non-existent-path-12345")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]


def test_unhandled_internal_server_error() -> None:
    client_no_raise = TestClient(app, raise_server_exceptions=False)
    response = client_no_raise.get("/test-errors/server-error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Verify no raw traceback is exposed
    assert "Unexpected internal crash" not in data["error"]["message"]
    assert "request_id" in data["error"]


def test_validation_error_format(client: TestClient) -> None:
    response = client.post(
        "/test-errors/validation",
        json={"name": "Alice", "age": "invalid_number"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0
    assert data["error"]["details"][0]["field"] == "body.age"
