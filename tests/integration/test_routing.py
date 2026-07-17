"""Testes de integração — Roteamento."""


async def test_simulate_pix_routes_to_rede(client, auth_headers):
    res = await client.post(
        "/api/v1/routing/simulate",
        json={"method": "pix", "amount": 10000, "fraud_score": 90},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["blocked"] is False
    assert data["acquirer"] == "rede"
    assert len(data["trail"]) > 0


async def test_simulate_low_fraud_score_blocks(client, auth_headers):
    res = await client.post(
        "/api/v1/routing/simulate",
        json={"method": "credit", "amount": 10000, "fraud_score": 30},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["blocked"] is True
    assert data["acquirer"] is None
    assert "antifraude" in data["block_reason"].lower()


async def test_simulate_invalid_amount_rejected(client, auth_headers):
    res = await client.post(
        "/api/v1/routing/simulate",
        json={"method": "pix", "amount": 0, "fraud_score": 90},
        headers=auth_headers,
    )
    assert res.status_code == 422


async def test_list_rules(client, auth_headers):
    res = await client.get("/api/v1/routing/rules", headers=auth_headers)
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) > 0
    assert all("name" in r and "action" in r for r in rules)


async def test_routing_requires_auth(client):
    res = await client.get("/api/v1/routing/rules")
    assert res.status_code == 401
