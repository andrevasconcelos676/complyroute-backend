"""Endpoints de Conciliação — /api/v1/reconciliation"""

from datetime import date, datetime, time, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.transaction import Transaction

router = APIRouter()


@router.get("/summary")
async def reconciliation_summary(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Resumo de conciliação por subadquirente no período."""
    # created_at é armazenado em UTC — "hoje" precisa ser a data UTC, não a data local
    # do processo, e precisa ser recalculada a cada requisição (não fixada em import time).
    today_utc = datetime.now(timezone.utc).date()
    date_from = date_from or today_utc
    date_to = date_to or today_utc

    # date_to é inclusivo do dia inteiro — comparar contra o início do dia seguinte,
    # já que created_at tem componente de hora e um "<=" contra a data pura excluiria
    # qualquer transação do próprio dia feita após a meia-noite.
    range_start = datetime.combine(date_from, time.min)
    range_end = datetime.combine(date_to + timedelta(days=1), time.min)

    q = (
        select(
            Transaction.acquirer,
            func.count(Transaction.id).label("total_txns"),
            func.sum(Transaction.amount).label("gross_volume"),
            func.sum(Transaction.amount).filter(Transaction.status == "approved").label("approved_volume"),
        )
        .where(
            and_(
                Transaction.created_at >= range_start,
                Transaction.created_at < range_end,
                Transaction.status.in_(["approved", "refunded", "chargeback"]),
            )
        )
        .group_by(Transaction.acquirer)
    )
    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "acquirer": row.acquirer,
            "total_txns": row.total_txns,
            "gross_volume": row.gross_volume or 0,
            "approved_volume": row.approved_volume or 0,
            "status": "reconciled",
        }
        for row in rows
    ]
