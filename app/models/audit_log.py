"""Modelo ORM — Log de auditoria."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str]    = mapped_column(String(100), nullable=False, index=True)   # "transaction.create"
    resource: Mapped[str]  = mapped_column(String(50), nullable=False)               # "transaction"
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None]  = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None]  = mapped_column(String(512), nullable=True)
    payload: Mapped[dict | None]    = mapped_column(JSON, nullable=True)
    result: Mapped[str]    = mapped_column(String(20), nullable=False, default="success")  # success | failure

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
