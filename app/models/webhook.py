"""Modelos ORM — Webhooks e entregas."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url: Mapped[str]      = mapped_column(String(2048), nullable=False)
    events: Mapped[list]  = mapped_column(JSON, nullable=False, default=list)  # ["payment.approved", ...]
    secret: Mapped[str | None] = mapped_column(String(256), nullable=True)     # HMAC secret individual
    is_active: Mapped[bool]    = mapped_column(Boolean, default=True)
    success_rate: Mapped[float] = mapped_column(default=100.0)

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(back_populates="webhook", lazy="dynamic")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("webhooks.id"), nullable=False, index=True)
    event: Mapped[str]          = mapped_column(String(100), nullable=False)
    payload: Mapped[dict]       = mapped_column(JSON, nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None]   = mapped_column(Text, nullable=True)
    attempt: Mapped[int]        = mapped_column(Integer, default=1)
    success: Mapped[bool]       = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    webhook: Mapped["Webhook"] = relationship(back_populates="deliveries")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
