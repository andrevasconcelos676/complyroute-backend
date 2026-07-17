"""Testes de integração — Webhooks."""

import uuid


async def test_create_and_list_webhook(client, auth_headers):
    res = await client.post(
        "/api/v1/webhooks",
        json={"url": "https://app.empresa.com/webhooks/pay", "events": ["payment.approved", "payment.refunded"]},
        headers=auth_headers,
    )
    assert res.status_code == 201
    created = res.json()
    assert created["url"] == "https://app.empresa.com/webhooks/pay"
    assert created["events"] == ["payment.approved", "payment.refunded"]

    res = await client.get("/api/v1/webhooks", headers=auth_headers)
    assert res.status_code == 200
    assert any(w["id"] == created["id"] for w in res.json())


async def test_delete_webhook(client, auth_headers):
    created = await client.post(
        "/api/v1/webhooks", json={"url": "https://x.com/hook", "events": []}, headers=auth_headers
    )
    wh_id = created.json()["id"]

    res = await client.delete(f"/api/v1/webhooks/{wh_id}", headers=auth_headers)
    assert res.status_code == 204

    res = await client.get("/api/v1/webhooks", headers=auth_headers)
    assert all(w["id"] != wh_id for w in res.json())


async def test_delete_nonexistent_webhook(client, auth_headers):
    res = await client.delete(f"/api/v1/webhooks/{uuid.uuid4()}", headers=auth_headers)
    assert res.status_code == 404


async def test_webhooks_require_auth(client):
    res = await client.get("/api/v1/webhooks")
    assert res.status_code == 401
