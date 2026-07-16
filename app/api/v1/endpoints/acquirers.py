"""Endpoints de Subadquirentes — /api/v1/acquirers"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.acquirer import Acquirer

router = APIRouter()


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
