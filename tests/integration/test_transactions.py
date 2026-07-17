"""Testes de integração — Transações."""

import uuid

PIX_PAYLOAD = {
    "amount": 15000,
    "method": "pix",
    "customer": {"name": "Maria Silva", "document": "12345678900", "email": "maria@example.com"},
}


async def test_create_pix_transaction_routes_to_rede(client, auth_headers):
    res = await client.post("/api/v1/transactions", json=PIX_PAYLOAD, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "approved"
    assert data["acquirer"] == "rede"
    assert data["amount"] == 15000


async def test_create_transaction_invalid_method(client, auth_headers):
    payload = {**PIX_PAYLOAD, "method": "crypto"}
    res = await client.post("/api/v1/transactions", json=payload, headers=auth_headers)
    assert res.status_code == 422


async def test_create_transaction_requires_auth(client):
    res = await client.post("/api/v1/transactions", json=PIX_PAYLOAD)
    assert res.status_code == 401


async def test_list_transactions(client, auth_headers):
    await client.post("/api/v1/transactions", json=PIX_PAYLOAD, headers=auth_headers)

    res = await client.get("/api/v1/transactions", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_get_transaction_by_id(client, auth_headers):
    created = await client.post("/api/v1/transactions", json=PIX_PAYLOAD, headers=auth_headers)
    txn_id = created.json()["id"]

    res = await client.get(f"/api/v1/transactions/{txn_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == txn_id


async def test_get_transaction_not_found(client, auth_headers):
    res = await client.get(f"/api/v1/transactions/{uuid.uuid4()}", headers=auth_headers)
    assert res.status_code == 404


async def test_refund_approved_transaction(client, auth_headers):
    created = await client.post("/api/v1/transactions", json=PIX_PAYLOAD, headers=auth_headers)
    txn_id = created.json()["id"]

    res = await client.post(
        f"/api/v1/transactions/{txn_id}/refund",
        json={"reason": "cliente desistiu"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "refunded"


async def test_refund_already_refunded_transaction_fails(client, auth_headers):
    created = await client.post("/api/v1/transactions", json=PIX_PAYLOAD, headers=auth_headers)
    txn_id = created.json()["id"]
    await client.post(f"/api/v1/transactions/{txn_id}/refund", json={}, headers=auth_headers)

    res = await client.post(f"/api/v1/transactions/{txn_id}/refund", json={}, headers=auth_headers)
    assert res.status_code == 422


async def test_refund_nonexistent_transaction(client, auth_headers):
    res = await client.post(f"/api/v1/transactions/{uuid.uuid4()}/refund", json={}, headers=auth_headers)
    assert res.status_code == 404
