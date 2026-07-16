"""Modelo ORM — Subadquirentes."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Acquirer(Base):
    __tablename__ = "acquirers"

    id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)   # cielo, rede, stone…
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_url: Mapped[str]   = mapped_column(String(500), nullable=False)

    # ── Status ───────────────────────────────────────────────
    is_active: Mapped[bool]     = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool]    = mapped_column(Boolean, default=False)
    is_fallback: Mapped[bool]   = mapped_column(Boolean, default=False)
    priority: Mapped[int]       = mapped_column(Integer, default=10)   # menor = mais prioritário
    traffic_pct: Mapped[float]  = mapped_column(Float, default=0.0)    # % do tráfego atual

    # ── Suporte por método ───────────────────────────────────
    supports_credit: Mapped[bool]  = mapped_column(Boolean, default=True)
    supports_debit: Mapped[bool]   = mapped_column(Boolean, default=True)
    supports_pix: Mapped[bool]     = mapped_column(Boolean, default=True)
    supports_boleto: Mapped[bool]  = mapped_column(Boolean, default=True)

    # ── Métricas ─────────────────────────────────────────────
    approval_rate: Mapped[float]   = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[int]    = mapped_column(Integer, default=0)

    # ── Credenciais (criptografadas) ─────────────────────────
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
