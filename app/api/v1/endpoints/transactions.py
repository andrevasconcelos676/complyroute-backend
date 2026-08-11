"""Endpoints de Transações — /api/v1/transactions"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.exceptions import NotFoundError, FraudBlockError, RoutingError, AcquirerError
from app.db.session import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionList,
    RefundRequest,
)
from app.services.routing_engine import routing_engine, TransactionContext
from app.services.fraud_engine import fraud_engine, FraudContext
from app.services.acquirers import AcquirerClientFactory

router = APIRouter()
log = structlog.get_logger()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Processa uma nova transação pelo gateway.

    Fluxo:
    1. Análise antifraude (score 0–100)
    2. Motor de roteamento (seleciona subadquirente)
    3. Envio ao subadquirente
    4. Persistência e resposta
    """
    log.info("transaction.create.start", method=payload.method, amount=payload.amount)

    # ── 1. Antifraude ─────────────────────────────────────────
    fraud_ctx = FraudContext(
        ip_address=payload.metadata.get("ip_address", "0.0.0.0") if payload.metadata else "0.0.0.0",
        device_fingerprint=payload.metadata.get("device_fingerprint") if payload.metadata else None,
        card_bin=payload.card.number[:6] if payload.card else None,
        card_country=payload.card.country if payload.card else "BR",
        customer_document=payload.customer.document,
        customer_email=payload.customer.email,
        amount=payload.amount,
        method=payload.method,
    )
    fraud_result = await fraud_engine.evaluate(fraud_ctx)

    if fraud_result.blocked:
        txn = Transaction(
            amount=payload.amount,
            currency=payload.currency,
            method=payload.method,
            installments=payload.installments,
            status="declined",
            fraud_score=fraud_result.score,
            fraud_blocked=True,
            customer_name=payload.customer.name,
            customer_document=payload.customer.document,
            customer_email=payload.customer.email,
            card_last4=payload.card.number[-4:] if payload.card else None,
            card_country=payload.card.country if payload.card else "BR",
            card_bin=fraud_ctx.card_bin,
            error_message=fraud_result.block_reason,
            metadata_=payload.metadata,
        )
        db.add(txn)
        await db.flush()
        raise FraudBlockError(fraud_result.score)

    # ── 2. Roteamento ─────────────────────────────────────────
    routing_ctx = TransactionContext(
        method=payload.method,
        amount=payload.amount,
        installments=payload.installments,
        card_country=payload.card.country if payload.card else "BR",
        fraud_score=fraud_result.score,
        metadata=payload.metadata or {},
    )
    decision = routing_engine.evaluate(routing_ctx)

    if decision.blocked:
        raise RoutingError(decision.block_reason or "Transação bloqueada pelo motor de roteamento.")

    # ── 3. Envio ao subadquirente ─────────────────────────────
    acquirer_client = AcquirerClientFactory.get(decision.acquirer)

    if acquirer_client is not None:
        try:
            sale_result = await acquirer_client.create_sale(payload)
        except AcquirerError as e:
            txn = Transaction(
                amount=payload.amount,
                currency=payload.currency,
                method=payload.method,
                installments=payload.installments,
                status="declined",
                acquirer=decision.acquirer,
                routing_rule_applied=decision.trail[0].name if decision.trail else None,
                fraud_score=fraud_result.score,
                customer_name=payload.customer.name,
                customer_document=payload.customer.document,
                customer_email=payload.customer.email,
                card_last4=payload.card.number[-4:] if payload.card else None,
                card_country=payload.card.country if payload.card else "BR",
                card_bin=fraud_ctx.card_bin,
                error_message=e.message,
                metadata_=payload.metadata,
            )
            db.add(txn)
            await db.flush()
            raise
        finally:
            await acquirer_client.aclose()

        acquirer_response = {
            "status": sale_result.status,
            "acquirer_txn_id": sale_result.acquirer_txn_id,
            "authorization_code": sale_result.authorization_code,
            "nsu": sale_result.nsu,
            "latency_ms": sale_result.latency_ms,
        }
    else:
        # Simulação de resposta — subadquirentes sem integração real configurada.
        acquirer_response = {
            "status": "approved",
            "authorization_code": "SIM-" + uuid.uuid4().hex[:6].upper(),
            "nsu": uuid.uuid4().hex[:8].upper(),
            "latency_ms": 312,
        }

    # ── 4. Persistência ───────────────────────────────────────
    txn = Transaction(
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        installments=payload.installments,
        status=acquirer_response["status"],
        acquirer=decision.acquirer,
        acquirer_txn_id=acquirer_response.get("acquirer_txn_id"),
        authorization_code=acquirer_response.get("authorization_code"),
        nsu=acquirer_response.get("nsu"),
        routing_rule_applied=decision.trail[0].name if decision.trail else None,
        fraud_score=fraud_result.score,
        customer_name=payload.customer.name,
        customer_document=payload.customer.document,
        customer_email=payload.customer.email,
        card_last4=payload.card.number[-4:] if payload.card else None,
        card_country=payload.card.country if payload.card else "BR",
        card_bin=fraud_ctx.card_bin,
        latency_ms=acquirer_response.get("latency_ms"),
        metadata_=payload.metadata,
        approved_at=datetime.now(timezone.utc) if acquirer_response["status"] == "approved" else None,
    )
    db.add(txn)
    await db.flush()

    log.info("transaction.create.done", txn_id=str(txn.id), status=txn.status, acquirer=txn.acquirer)

    # TODO: disparar webhook assíncrono via Celery
    # send_webhook.delay("payment." + txn.status, txn.id)

    return txn


@router.get("", response_model=TransactionList)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    status: str | None = Query(None),
    method: str | None = Query(None),
    acquirer: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista transações com filtros e paginação."""
    q = select(Transaction).order_by(Transaction.created_at.desc())

    if status:
        q = q.where(Transaction.status == status)
    if method:
        q = q.where(Transaction.method == method)
    if acquirer:
        q = q.where(Transaction.acquirer == acquirer)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    q = q.offset((page - 1) * limit).limit(limit)
    items = (await db.execute(q)).scalars().all()

    return TransactionList(items=items, total=total, page=page, limit=limit)


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(txn_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Busca uma transação pelo ID."""
    txn = await db.get(Transaction, txn_id)
    if not txn:
        raise NotFoundError("Transação", str(txn_id))
    return txn


@router.post("/{txn_id}/refund", response_model=TransactionResponse)
async def refund_transaction(
    txn_id: uuid.UUID,
    payload: RefundRequest,
    db: AsyncSession = Depends(get_db),
):
    """Solicita estorno de uma transação aprovada."""
    txn = await db.get(Transaction, txn_id)
    if not txn:
        raise NotFoundError("Transação", str(txn_id))

    if txn.status != "approved":
        from app.core.exceptions import ValidationError
        raise ValidationError(f"Transação com status '{txn.status}' não pode ser estornada.")

    acquirer_client = AcquirerClientFactory.get(txn.acquirer)
    if acquirer_client is not None and txn.acquirer_txn_id:
        try:
            sale_result = await acquirer_client.refund_sale(txn.acquirer_txn_id, payload.amount)
        finally:
            await acquirer_client.aclose()
        txn.status = sale_result.status
    else:
        # Simulação — subadquirentes sem integração real configurada.
        txn.status = "refunded"
    await db.flush()

    log.info("transaction.refund", txn_id=str(txn_id), amount=payload.amount)
    return txn
