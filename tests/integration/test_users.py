"""Testes de integração — Usuários."""

import uuid


async def test_create_user(client, auth_headers):
    res = await client.post(
        "/api/v1/users",
        json={"name": "Novo Usuário", "email": "novo@complyroute.com.br", "password": "SenhaForte@123", "role": "financial"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "novo@complyroute.com.br"
    assert data["role"] == "financial"


async def test_create_user_defaults_to_readonly_role(client, auth_headers):
    res = await client.post(
        "/api/v1/users",
        json={"name": "Sem Role", "email": "semrole@complyroute.com.br", "password": "SenhaForte@123"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["role"] == "readonly"


async def test_list_users(client, auth_headers, admin_user):
    res = await client.get("/api/v1/users", headers=auth_headers)
    assert res.status_code == 200
    emails = [u["email"] for u in res.json()]
    assert admin_user.email in emails


async def test_update_user(client, auth_headers):
    created = await client.post(
        "/api/v1/users",
        json={"name": "Editar Nome", "email": "editar@complyroute.com.br", "password": "SenhaForte@123"},
        headers=auth_headers,
    )
    user_id = created.json()["id"]

    res = await client.patch(f"/api/v1/users/{user_id}", json={"name": "Nome Atualizado"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Nome Atualizado"


async def test_update_nonexistent_user(client, auth_headers):
    res = await client.patch(f"/api/v1/users/{uuid.uuid4()}", json={"name": "X"}, headers=auth_headers)
    assert res.status_code == 404


async def test_delete_user_is_soft_delete(client, auth_headers):
    created = await client.post(
        "/api/v1/users",
        json={"name": "Vai Sumir", "email": "vaisumir@complyroute.com.br", "password": "SenhaForte@123"},
        headers=auth_headers,
    )
    user_id = created.json()["id"]

    res = await client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
    assert res.status_code == 204

    res = await client.get("/api/v1/users", headers=auth_headers)
    deleted = next(u for u in res.json() if u["id"] == user_id)
    assert deleted["is_active"] is False


async def test_delete_nonexistent_user(client, auth_headers):
    res = await client.delete(f"/api/v1/users/{uuid.uuid4()}", headers=auth_headers)
    assert res.status_code == 404


async def test_users_require_auth(client):
    res = await client.get("/api/v1/users")
    assert res.status_code == 401
