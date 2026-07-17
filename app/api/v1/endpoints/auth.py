"""Endpoints de Autenticação — /api/v1/auth"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.exceptions import AuthenticationError
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenResponse

router = APIRouter()
log = structlog.get_logger()


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica usuário e retorna tokens JWT."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        log.warning("auth.login.failed", email=payload.email)
        raise AuthenticationError("E-mail ou senha incorretos.")

    if not user.is_active:
        raise AuthenticationError("Conta desativada. Contate o administrador.")

    # 2FA
    if user.is_2fa_enabled:
        if not payload.totp_code:
            return LoginResponse(requires_2fa=True, access_token=None, refresh_token=None, user=None)

        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(payload.totp_code):
            raise AuthenticationError("Código 2FA inválido.")

    access_token = create_access_token(str(user.id), {"role": user.role})
    refresh_token = create_refresh_token(str(user.id))

    log.info("auth.login.success", user_id=str(user.id), role=user.role)

    return LoginResponse(
        requires_2fa=False,
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": str(user.id), "name": user.name, "email": user.email, "role": user.role},
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Renova o access token usando o refresh token."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise AuthenticationError("Token inválido.")
        user_id = uuid.UUID(data["sub"])
    except AuthenticationError:
        raise
    except Exception:
        raise AuthenticationError("Refresh token inválido ou expirado.")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("Usuário não encontrado.")

    access_token = create_access_token(str(user.id), {"role": user.role})
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    Logout do usuário.
    Em produção: adicionar o token em uma blocklist no Redis.
    """
    return None
