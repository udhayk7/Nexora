import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, cast

from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_request_id, logger, sanitize_data


class AuditEvent(BaseModel):
    """Immutable audit event representing a significant application action."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_type: str = Field(..., description="Type of actor: user, system, service, anonymous")
    actor_id: Optional[str] = Field(default=None, description="Identifier of the actor")
    action: str = Field(..., description="Action performed, e.g. auth.login, resume.upload")
    resource_type: str = Field(
        ..., description="Target resource type, e.g. user, resume, application, job"
    )
    resource_id: Optional[str] = Field(
        default=None, description="Identifier of the targeted resource"
    )
    request_id: str = Field(default_factory=get_request_id)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def sanitize_metadata_payload(cls, v: Any) -> dict[str, Any]:
        """Strip sensitive secrets or credentials from audit event metadata."""
        if not isinstance(v, dict):
            return {}
        return cast(dict[str, Any], sanitize_data(v))

    model_config = {
        "frozen": True,
    }


class AuditEventSink(Protocol):
    """Protocol for audit event dispatchers."""

    def emit(self, event: AuditEvent) -> None:
        """Emit or persist an audit event."""
        ...


class LoggingAuditSink:
    """Default audit event sink emitting structured logs to the 'nexora.audit' logger."""

    def __init__(self) -> None:
        self._audit_logger = logger.getChild("audit")

    def emit(self, event: AuditEvent) -> None:
        self._audit_logger.info(
            f"AUDIT_EVENT action={event.action} "
            f"resource={event.resource_type}:{event.resource_id} "
            f"actor={event.actor_type}:{event.actor_id} "
            f"req={event.request_id} data={event.metadata}"
        )


class AuditService:
    """Service to record and route audit events across the platform."""

    def __init__(self, sink: Optional[AuditEventSink] = None) -> None:
        self._sink: AuditEventSink = sink or LoggingAuditSink()

    def record_event(
        self,
        action: str,
        resource_type: str,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create, sanitize, and dispatch an audit event."""
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_id=resource_id,
            request_id=get_request_id(),
            metadata=metadata or {},
        )
        self._sink.emit(event)
        return event


# Global default audit service instance
audit_service = AuditService()
