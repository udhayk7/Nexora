from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.core.audit import AuditEvent, AuditService, LoggingAuditSink


def test_audit_event_creation() -> None:
    event = AuditEvent(
        actor_type="user",
        actor_id="user_123",
        action="resume.upload",
        resource_type="resume",
        resource_id="res_456",
        metadata={"filename": "resume.pdf", "size_bytes": 1024},
    )
    assert event.actor_id == "user_123"
    assert event.action == "resume.upload"
    assert event.resource_type == "resume"
    assert event.resource_id == "res_456"
    assert event.metadata["filename"] == "resume.pdf"
    assert event.event_id is not None
    assert event.timestamp is not None


def test_audit_event_sanitizes_metadata() -> None:
    event = AuditEvent(
        actor_type="user",
        actor_id="user_123",
        action="auth.login",
        resource_type="user",
        resource_id="user_123",
        metadata={
            "ip_address": "127.0.0.1",
            "password": "my_secret_password",
            "token": "secret_jwt_token",
        },
    )
    assert event.metadata["ip_address"] == "127.0.0.1"
    assert event.metadata["password"] == "[REDACTED]"
    assert event.metadata["token"] == "[REDACTED]"


def test_audit_event_immutability() -> None:
    event = AuditEvent(
        actor_type="system",
        action="system.startup",
        resource_type="system",
    )
    with pytest.raises(ValidationError):
        # Model is frozen
        event.action = "system.shutdown"  # type: ignore[misc]


def test_audit_service_dispatch() -> None:
    mock_sink = MagicMock()
    service = AuditService(sink=mock_sink)

    created_event = service.record_event(
        action="job.bookmark",
        resource_type="job",
        actor_type="user",
        actor_id="user_999",
        resource_id="job_888",
        metadata={"title": "Software Engineer"},
    )

    mock_sink.emit.assert_called_once_with(created_event)
    assert created_event.action == "job.bookmark"


def test_logging_audit_sink() -> None:
    sink = LoggingAuditSink()
    event = AuditEvent(
        actor_type="service",
        action="test.action",
        resource_type="test",
    )
    # Should execute without throwing any exception
    sink.emit(event)
