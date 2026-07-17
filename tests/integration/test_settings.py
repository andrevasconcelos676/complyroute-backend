"""Testes de integração — Configurações."""


async def test_get_settings(client, auth_headers):
    res = await client.get("/api/v1/settings", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["app_name"] == "ComplyRoute"
    assert "txn_max_amount" in data
    assert "fraud_score_min_auto_approve" in data
    # Segredos nunca devem vazar nesta rota pública de configurações.
    assert "SECRET_KEY" not in data
    assert "secret_key" not in data


async def test_settings_requires_auth(client):
    res = await client.get("/api/v1/settings")
    assert res.status_code == 401
