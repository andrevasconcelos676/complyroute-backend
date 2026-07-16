"""Modelo ORM — Transações processadas pelo gateway."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Valores ──────────────────────────────────────────────
    amount: Mapped[int]     = mapped_column(BigInteger, nullable=False)           # centavos
    currency: Mapped[str]   = mapped_column(String(3), nullable=False, default="BRL")
    installments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Método ───────────────────────────────────────────────
    method: Mapped[str] = mapped_column(
        Enum("credit", "debit", "pix", "boleto", name="payment_method"),
        nullable=False,
    )

    # ── Status ───────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "approved", "declined", "refunded", "chargeback", name="txn_status"),
        nullable=False,
        default="pending",
        index=True,
    )

    # ── Roteamento ───────────────────────────────────────────
    acquirer: Mapped[str | None]   = mapped_column(String(50), nullable=True, index=True)
    acquirer_txn_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authorization_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nsu: Mapped[str | None]        = mapped_column(String(50), nullable=True)
    routing_rule_applied: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Antifraude ───────────────────────────────────────────
    fraud_score: Mapped[int | None]   = mapped_column(Integer, nullable=True)
    fraud_blocked: Mapped[bool]       = mapped_column(default=False)

    # ── Pagador ──────────────────────────────────────────────
    customer_name: Mapped[str]     = mapped_column(String(255), nullable=False)
    customer_document: Mapped[str] = mapped_column(String(20), nullable=False)    # CPF/CNPJ
    customer_email: Mapped[str]    = mapped_column(String(255), nullable=False)

    # ── Cartão (dados mascarados) ─────────────────────────────
    card_last4: Mapped[str | None]  = mapped_column(String(4), nullable=True)
    card_brand: Mapped[str | None]  = mapped_column(String(30), nullable=True)
    card_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    card_bin: Mapped[str | None]    = mapped_column(String(6), nullable=True)

    # ── Performance ──────────────────────────────────────────
    latency_ms: Mapped[int | None]  = mapped_column(Integer, nullable=True)
    retries: Mapped[int]            = mapped_column(Integer, default=0)

    # ── Metadados ────────────────────────────────────────────
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Transaction {self.id} | {self.method} R${self.amount/100:.2f} [{self.status}]>"
