"""Schemas Pydantic — Transações."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CardData(BaseModel):
    number: str = Field(min_length=13, max_length=19)
    holder: str
    expiry: str                  # MM/YYYY
    cvv: str = Field(min_length=3, max_length=4)
    country: str = Field(default="BR", max_length=2)


class CustomerData(BaseModel):
    name: str
    document: str                # CPF ou CNPJ (sem formatação)
    email: str


class TransactionCreate(BaseModel):
    amount: int = Field(gt=0, description="Valor em centavos. Ex.: R$ 15,00 = 1500")
    currency: str = Field(default="BRL", max_length=3)
    method: str = Field(description="credit | debit | pix | boleto")
    installments: int = Field(default=1, ge=1, le=18)
    card: CardData | None = None
    customer: CustomerData
    metadata: dict[str, Any] | None = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        allowed = {"credit", "debit", "pix", "boleto"}
        if v not in allowed:
            raise ValueError(f"Método inválido. Use: {', '.join(allowed)}")
        return v


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    currency: str
    method: str
    installments: int
    status: str
    acquirer: str | None
    authorization_code: str | None
    nsu: str | None
    fraud_score: int | None
    customer_name: str
    card_last4: str | None
    latency_ms: int | None
    created_at: datetime
    approved_at: datetime | None

    class Config:
        from_attributes = True


class TransactionList(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    limit: int


class RefundRequest(BaseModel):
    amount: int | None = Field(None, description="Valor em centavos. Se omitido, estorno total.")
    reason: str | None = None
