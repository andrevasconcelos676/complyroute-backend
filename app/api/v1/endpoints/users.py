"""Endpoints de Usuários — /api/v1/users"""

import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.name))
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(payload: dict, db: AsyncSession = Depends(get_db)):
    user = User(
        name=payload["name"],
        email=payload["email"],
        password_hash=hash_password(payload["password"]),
        role=payload.get("role", "readonly"),
    )
    db.add(user)
    await db.flush()
    return user


@router.patch("/{user_id}")
async def update_user(user_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário", str(user_id))
    for k, v in payload.items():
        if hasattr(user, k) and k not in ("id", "password_hash"):
            setattr(user, k, v)
    await db.flush()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário", str(user_id))
    user.is_active = False   # soft delete
    await db.flush()
