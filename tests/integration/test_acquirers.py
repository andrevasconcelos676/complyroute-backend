"""Testes de integração — Subadquirentes."""

import base64
import hashlib
import hmac
import json
import time
import uuid

from app.core.config import settings
from app.models.acquirer import Acquirer
from app.models.transaction import Transaction

NECTA_WEBHOOK_SECRET = "whsec_" + base64.b64encode(b"test-necta-secret").decode()


def _sign_necta_event(body: bytes, svix_id: str, timestamp: str) -> str:
    secret_bytes = base64.b64decode(NECTA_WEBHOOK_SECRET.removeprefix("whsec_"))
    signed_content = f"{svix_id}.{timestamp}.{body.decode()}".encode()
    sig = base64.b64encode(hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()).decode()
    return f"v1,{sig}"


def _necta_headers(body: bytes) -> dict:
    svix_id = f"msg_{uuid.uuid4().hex[:8]}"
    timestamp = str(int(time.time()))
    return {
        "svix-id": svix_id,
        "svix-timestamp": timestamp,
        "svix-signature": _sign_necta_event(body, svix_id, timestamp),
    }


async def _seed_acquirer(db_session, **overrides):
    defaults = dict(
        name="cielo",
        display_name="Cielo",
        api_url="https://api.cielo.com.br",
        priority=1,
        is_primary=True,
    )
    defaults.update(overrides)
    acq = Acquirer(**defaults)
    db_session.add(acq)
    await db_session.commit()
    return acq


async def test_list_acquirers_empty(client, auth_headers):
    res = await client.get("/api/v1/acquirers", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


async def test_list_acquirers_ordered_by_priority(client, auth_headers, db_session):
    await _seed_acquirer(db_session, name="stone", display_name="Stone", api_url="https://api.stone.com.br", priority=5)
    await _seed_acquirer(db_session, name="rede", display_name="Rede", api_url="https://api.rede.com.br", priority=2)

    res = await client.get("/api/v1/acquirers", headers=auth_headers)
    assert res.status_code == 200
    names = [a["name"] for a in res.json()]
    assert names == ["rede", "stone"]


async def test_get_acquirer_status(client, auth_headers, db_session):
    await _seed_acquirer(db_session, name="pagseguro", display_name="PagSeguro", api_url="https://api.pagseguro.com")

    res = await client.get("/api/v1/acquirers/pagseguro/status", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "pagseguro"


async def test_get_acquirer_status_not_found(client, auth_headers):
    res = await client.get("/api/v1/acquirers/inexistente/status", headers=auth_headers)
    assert res.status_code == 404


async def test_acquirers_requires_auth(client):
    res = await client.get("/api/v1/acquirers")
    assert res.status_code == 401


async def _seed_transaction(db_session, **overrides):
    defaults = dict(
        amount=1500,
        currency="BRL",
        method="pix",
        status="processing",
        acquirer="necta",
        acquirer_txn_id="sale-uuid-1",
        customer_name="Maria Silva",
        customer_document="12345678900",
        customer_email="maria@example.com",
    )
    defaults.update(overrides)
    txn = Transaction(**defaults)
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)
    return txn


async def test_necta_webhook_marks_sale_paid(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "NECTA_WEBHOOK_SECRET", NECTA_WEBHOOK_SECRET)
    txn = await _seed_transaction(db_session)

    body = json.dumps({
        "type": "sale.paid",
        "id": "sale-uuid-1",
        "status": "paid",
        "occurredAt": "2026-07-28T14:03:22.481Z",
        "marketplaceId": str(uuid.uuid4()),
    }).encode()

    res = await client.post(
        "/api/v1/acquirers/necta/webhook",
        content=body,
        headers={**_necta_headers(body), "Content-Type": "application/json"},
    )
    assert res.status_code == 200

    await db_session.refresh(txn)
    assert txn.status == "approved"
    assert txn.approved_at is not None


async def test_necta_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "NECTA_WEBHOOK_SECRET", NECTA_WEBHOOK_SECRET)
    body = json.dumps({"type": "sale.paid", "id": "sale-uuid-1"}).encode()

    res = await client.post(
        "/api/v1/acquirers/necta/webhook",
        content=body,
        headers={"svix-id": "msg_1", "svix-timestamp": str(int(time.time())), "svix-signature": "v1,invalid"},
    )
    assert res.status_code == 401


async def test_necta_webhook_unknown_sale_still_returns_200(client, monkeypatch):
    monkeypatch.setattr(settings, "NECTA_WEBHOOK_SECRET", NECTA_WEBHOOK_SECRET)
    body = json.dumps({"type": "sale.paid", "id": "sale-does-not-exist"}).encode()

    res = await client.post(
        "/api/v1/acquirers/necta/webhook",
        content=body,
        headers=_necta_headers(body),
    )
    assert res.status_code == 200
