"""Modelo ORM — Regras de Roteamento."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    priority: Mapped[int]   = mapped_column(Integer, nullable=False, unique=True, index=True)
    name: Mapped[str]       = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Condição (JSON) ──────────────────────────────────────
    # Ex.: {"field": "method", "operator": "eq", "value": "pix"}
    # Ex.: {"field": "amount", "operator": "gt", "value": 10000}
    condition: Mapped[dict] = mapped_column(JSON, nullable=False)

    # ── Ação ─────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "route" | "block" | "retry"
    target_acquirer: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Estado ───────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
