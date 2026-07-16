"""Schemas Pydantic — Roteamento."""

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    method: str = Field(description="credit | debit | pix | boleto")
    amount: int = Field(gt=0, description="Valor em centavos")
    installments: int = Field(default=1, ge=1, le=18)
    card_country: str = Field(default="BR")
    fraud_score: int = Field(default=85, ge=0, le=100)
    simulate_timeout: bool = Field(default=False)


class TrailItem(BaseModel):
    rule_id: int
    name: str
    matched: bool
    action: str | None
    target: str | None


class SimulationResponse(BaseModel):
    acquirer: str | None
    blocked: bool
    block_reason: str | None
    trail: list[TrailItem]
