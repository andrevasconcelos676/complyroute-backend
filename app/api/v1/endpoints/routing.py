"""Endpoints de Roteamento — /api/v1/routing"""

from fastapi import APIRouter
from app.schemas.routing import SimulationRequest, SimulationResponse
from app.services.routing_engine import routing_engine, TransactionContext

router = APIRouter()


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_routing(payload: SimulationRequest):
    """
    Simula o roteamento de uma transação sem processá-la.
    Retorna o subadquirente selecionado e a trilha de decisão.
    """
    ctx = TransactionContext(
        method=payload.method,
        amount=payload.amount,
        installments=payload.installments,
        card_country=payload.card_country,
        fraud_score=payload.fraud_score,
        primary_status="timeout" if payload.simulate_timeout else "ok",
    )
    decision = routing_engine.evaluate(ctx)
    return SimulationResponse(
        acquirer=decision.acquirer,
        blocked=decision.blocked,
        block_reason=decision.block_reason,
        trail=[{"rule_id": r.rule_id, "name": r.name, "matched": r.matched, "action": r.action, "target": r.target} for r in decision.trail],
    )


@router.get("/rules")
async def list_rules():
    """Lista todas as regras de roteamento ativas."""
    from app.services.routing_engine import RULES
    return [{"id": r["id"], "name": r["name"], "action": r["action"], "target": r.get("target"), "active": r.get("active", True)} for r in RULES]
