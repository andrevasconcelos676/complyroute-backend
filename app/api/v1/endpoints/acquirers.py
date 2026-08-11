"""Endpoints de Subadquirentes — /api/v1/acquirers"""

import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models.acquirer import Acquirer
from app.models.transaction import Transaction
from app.services.acquirers.necta import verify_necta_webhook_signature

router = APIRouter()
log = structlog.get_logger()


@router.get("")
async def list_acquirers(db: AsyncSession = Depends(get_db)):
    """Lista todos os subadquirentes e seus status."""
    result = await db.execute(select(Acquirer).order_by(Acquirer.priority))
    return result.scalars().all()


@router.get("/{name}/status")
async def get_acquirer_status(name: str, db: AsyncSession = Depends(get_db)):
    """Status detalhado de um subadquirente específico."""
    result = await db.execute(select(Acquirer).where(Acquirer.name == name))
    acq = result.scalar_one_or_none()
    if not acq:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Subadquirente", name)
    return acq


@router.post("/necta/webhook", status_code=status.HTTP_200_OK)
async def necta_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recebe eventos assíncronos da Necta Multi-Pay (`sale.paid`, `sale.refunded`,
    `sale.failed`, `seller.status_changed`) e atualiza a transação correspondente.

    Assinatura verificada no padrão Svix (`svix-id`/`svix-timestamp`/`svix-signature`)
    contra `NECTA_WEBHOOK_SECRET`. O mesmo evento pode chegar mais de uma vez
    (retentativa) — o processamento abaixo é idempotente por natureza (apenas
    reaplica o status).
    """
    body = await request.body()
    if not verify_necta_webhook_signature(body, request.headers, settings.NECTA_WEBHOOK_SECRET):
        raise AuthenticationError("Assinatura do webhook inválida.")

    event = json.loads(body)
    event_type = event.get("type")
    sale_id = event.get("id")

    result = await db.execute(select(Transaction).where(Transaction.acquirer_txn_id == sale_id))
    txn = result.scalar_one_or_none()
    if not txn:
        log.warning("necta.webhook.unknown_sale", sale_id=sale_id, type=event_type)
        return {"received": True}

    if event_type == "sale.paid":
        txn.status = "approved"
        txn.approved_at = datetime.now(timezone.utc)
    elif event_type == "sale.refunded":
        txn.status = "refunded"
    elif event_type == "sale.failed":
        txn.status = "declined"

    await db.flush()
    log.info("necta.webhook.processed", sale_id=sale_id, type=event_type, txn_id=str(txn.id))
    return {"received": True}
