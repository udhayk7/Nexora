import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AIUsageLog(Base):
    """Centralized audit log of AI provider requests, token counts, and estimated costs."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    feature: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    estimated_cost_usd: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    request_status: Mapped[str] = mapped_column(
        String(30),
        default="success",
        nullable=False,
        index=True,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    cache_hit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    request_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", lazy="joined")
