"""Endpoints de Conciliação — /api/v1/reconciliation"""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.transaction import Transaction

router = APIRouter()


@router.get("/summary")
async def reconciliation_summary(
    date_from: date = Query(default=date.today()),
    date_to: date = Query(default=date.today()),
    db: AsyncSession = Depends(get_db),
):
    """Resumo de conciliação por subadquirente no período."""
    q = (
        select(
            Transaction.acquirer,
            func.count(Transaction.id).label("total_txns"),
            func.sum(Transaction.amount).label("gross_volume"),
            func.sum(Transaction.amount).filter(Transaction.status == "approved").label("approved_volume"),
        )
        .where(
            and_(
                Transaction.created_at >= date_from,
                Transaction.created_at <= date_to,
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
