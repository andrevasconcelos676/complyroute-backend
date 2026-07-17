"""Testes de integração — Autenticação."""

from app.core.security import hash_password
from app.models.user import User


async def test_login_success(client, admin_user):
    res = await client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "Senha@Teste123",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["requires_2fa"] is False
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == admin_user.email


async def test_login_wrong_password(client, admin_user):
    res = await client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "senha-errada",
    })
    assert res.status_code == 401


async def test_login_unknown_email(client):
    res = await client.post("/api/v1/auth/login", json={
        "email": "ninguem@complyroute.com.br",
        "password": "qualquer",
    })
    assert res.status_code == 401


async def test_login_inactive_user_blocked(client, db_session):
    user = User(
        name="Inativo",
        email="inativo@complyroute.com.br",
        password_hash=hash_password("Senha@123"),
        role="readonly",
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    res = await client.post("/api/v1/auth/login", json={
        "email": "inativo@complyroute.com.br",
        "password": "Senha@123",
    })
    assert res.status_code == 401


async def test_refresh_token_flow(client, admin_user):
    login = await client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": "Senha@Teste123",
    })
    refresh_token = login.json()["refresh_token"]

    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert res.json()["access_token"]


async def test_refresh_with_invalid_token(client):
    res = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert res.status_code == 401


async def test_protected_route_requires_token(client):
    res = await client.get("/api/v1/acquirers")
    assert res.status_code == 401


async def test_protected_route_rejects_garbage_token(client):
    res = await client.get("/api/v1/acquirers", headers={"Authorization": "Bearer lixo"})
    assert res.status_code == 401


async def test_health_is_public(client):
    res = await client.get("/health")
    assert res.status_code == 200
