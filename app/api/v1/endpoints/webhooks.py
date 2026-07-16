"""Endpoints de Webhooks — /api/v1/webhooks"""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.webhook import Webhook
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("")
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    wh = Webhook(url=payload["url"], events=payload.get("events", []))
    db.add(wh)
    await db.flush()
    return wh


@router.delete("/{wh_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(wh_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    wh = await db.get(Webhook, wh_id)
    if not wh:
        raise NotFoundError("Webhook", str(wh_id))
    await db.delete(wh)
