"""Schemas Pydantic — Autenticação."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class LoginResponse(BaseModel):
    requires_2fa: bool
    access_token: str | None
    refresh_token: str | None
    user: dict | None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
