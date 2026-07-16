"""Utilitários de segurança: JWT, hashing de senha, HMAC para webhooks."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Senha ─────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────

def create_access_token(subject: str | Any, extra: dict | None = None) -> str:
    payload = {
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | Any) -> str:
    payload = {
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida um JWT. Lança JWTError se inválido."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── API Keys ──────────────────────────────────────────────

def generate_api_key_prefix(env: str = "live") -> str:
    """Retorna o prefixo correto para a chave (sk_live_ ou sk_test_)."""
    return f"sk_{env}_"


def hash_api_key(key: str) -> str:
    """Hash SHA-256 da chave — apenas o hash é armazenado no banco."""
    return hashlib.sha256(key.encode()).hexdigest()


# ── HMAC (Webhooks) ───────────────────────────────────────

def sign_webhook_payload(payload: bytes, secret: str | None = None) -> str:
    """Gera assinatura HMAC-SHA256 para payload de webhook."""
    key = (secret or settings.WEBHOOK_SECRET).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str | None = None) -> bool:
    """Verifica assinatura HMAC-SHA256 de webhook recebido."""
    expected = sign_webhook_payload(payload, secret)
    return hmac.compare_digest(expected, signature)
