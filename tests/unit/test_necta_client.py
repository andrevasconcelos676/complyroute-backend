"""Testes unitários — cliente Necta Multi-Pay (sem chamadas de rede reais)."""

import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest

from app.core.exceptions import AcquirerError
from app.schemas.transaction import CardData, CustomerData, TransactionCreate
from app.services.acquirers.necta import NectaClient, verify_necta_webhook_signature

BASE_URL = "https://necta.test"


def make_client(handler) -> NectaClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(base_url=BASE_URL, transport=transport)
    return NectaClient(client_secret="client_secret", secret_key="secret_key", base_url=BASE_URL, http_client=http_client)


def pix_payload(**overrides) -> TransactionCreate:
    data = {
        "amount": 1500,
        "method": "pix",
        "customer": CustomerData(name="Maria Silva", document="12345678900", email="maria@example.com"),
    }
    data.update(overrides)
    return TransactionCreate(**data)


class CallLog:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []


def auth_response(token: str = "jwt-token-1") -> httpx.Response:
    return httpx.Response(200, json={"token": token})


async def test_create_pix_sale_success():
    log = CallLog()

    def handler(request: httpx.Request) -> httpx.Response:
        log.calls.append((request.method, request.url.path))
        if request.url.path == "/auth":
            return auth_response()
        if request.url.path == "/sales":
            body = json.loads(request.content)
            assert body["paymentMethod"] == "pix"
            return httpx.Response(
                201,
                json={"id": "sale-uuid-1", "externalId": "ext-123", "status": {"name": "paid"}},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    client = make_client(handler)
    result = await client.create_sale(pix_payload())

    assert result.status == "approved"
    assert result.acquirer_txn_id == "sale-uuid-1"
    assert result.authorization_code == "ext-123"
    assert ("POST", "/auth") in log.calls
    assert ("POST", "/sales") in log.calls
    await client.aclose()


async def test_token_is_cached_across_calls():
    log = CallLog()

    def handler(request: httpx.Request) -> httpx.Response:
        log.calls.append((request.method, request.url.path))
        if request.url.path == "/auth":
            return auth_response()
        return httpx.Response(201, json={"id": "s1", "externalId": "e1", "status": {"name": "pending"}})

    client = make_client(handler)
    await client.create_sale(pix_payload())
    await client.create_sale(pix_payload())

    auth_calls = [c for c in log.calls if c == ("POST", "/auth")]
    assert len(auth_calls) == 1
    await client.aclose()


async def test_401_triggers_single_reauth_and_retry():
    state = {"sales_attempts": 0, "auth_attempts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            state["auth_attempts"] += 1
            return auth_response(token=f"jwt-{state['auth_attempts']}")
        if request.url.path == "/sales":
            state["sales_attempts"] += 1
            if state["sales_attempts"] == 1:
                return httpx.Response(401, json={"message": "expired"})
            return httpx.Response(201, json={"id": "s1", "externalId": "e1", "status": {"name": "paid"}})
        raise AssertionError("unexpected request")

    client = make_client(handler)
    result = await client.create_sale(pix_payload())

    assert result.status == "approved"
    assert state["auth_attempts"] == 2
    assert state["sales_attempts"] == 2
    await client.aclose()


async def test_gateway_error_raises_acquirer_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return auth_response()
        return httpx.Response(400, json={"message": "valor mínimo não atingido"})

    client = make_client(handler)
    with pytest.raises(AcquirerError):
        await client.create_sale(pix_payload())
    await client.aclose()


async def test_credit_card_without_card_data_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return auth_response()

    client = make_client(handler)
    payload = pix_payload(method="credit", card=None)
    with pytest.raises(AcquirerError):
        await client.create_sale(payload)
    await client.aclose()


async def test_debit_method_not_supported():
    def handler(request: httpx.Request) -> httpx.Response:
        return auth_response()

    client = make_client(handler)
    payload = pix_payload(method="debit")
    with pytest.raises(AcquirerError):
        await client.create_sale(payload)
    await client.aclose()


async def test_credit_card_body_splits_expiry():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return auth_response()
        if request.url.path == "/sales":
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": "s1", "externalId": "e1", "status": {"name": "paid"}})
        raise AssertionError("unexpected request")

    client = make_client(handler)
    payload = pix_payload(
        method="credit",
        installments=3,
        card=CardData(number="4111111111111111", holder="MARIA SILVA", expiry="12/2030", cvv="123"),
    )
    await client.create_sale(payload)

    card = captured["body"]["creditCard"]
    assert card["expirationMonth"] == "12"
    assert card["expirationYear"] == "2030"
    assert captured["body"]["paymentMethod"] == "credit_card"
    assert captured["body"]["installments"] == 3
    await client.aclose()


async def test_pix_forces_installments_to_one():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return auth_response()
        if request.url.path == "/sales":
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": "s1", "externalId": "e1", "status": {"name": "paid"}})
        raise AssertionError("unexpected request")

    client = make_client(handler)
    await client.create_sale(pix_payload(installments=5))

    assert captured["body"]["installments"] == 1
    assert captured["body"]["paymentMethod"] == "pix"
    await client.aclose()


async def test_refund_sale_maps_status():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth":
            return auth_response()
        if request.url.path == "/sales/sale-uuid-1/void":
            return httpx.Response(200, json={"id": "sale-uuid-1", "reverted": True, "status": "refunded"})
        raise AssertionError("unexpected request")

    client = make_client(handler)
    result = await client.refund_sale("sale-uuid-1")

    assert result.status == "refunded"
    assert result.acquirer_txn_id == "sale-uuid-1"
    await client.aclose()


# ── Assinatura de webhook (Svix) ─────────────────────────────

def sign(body: bytes, secret: str, svix_id: str, timestamp: str) -> str:
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed_content = f"{svix_id}.{timestamp}.{body.decode()}".encode()
    sig = base64.b64encode(hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()).decode()
    return f"v1,{sig}"


def test_verify_webhook_signature_accepts_valid():
    secret = "whsec_" + base64.b64encode(b"super-secret-key").decode()
    body = json.dumps({"type": "sale.paid", "id": "abc"}).encode()
    timestamp = str(int(time.time()))
    headers = {
        "svix-id": "msg_1",
        "svix-timestamp": timestamp,
        "svix-signature": sign(body, secret, "msg_1", timestamp),
    }
    assert verify_necta_webhook_signature(body, headers, secret) is True


def test_verify_webhook_signature_rejects_tampered_body():
    secret = "whsec_" + base64.b64encode(b"super-secret-key").decode()
    body = json.dumps({"type": "sale.paid", "id": "abc"}).encode()
    timestamp = str(int(time.time()))
    headers = {
        "svix-id": "msg_1",
        "svix-timestamp": timestamp,
        "svix-signature": sign(body, secret, "msg_1", timestamp),
    }
    tampered = json.dumps({"type": "sale.paid", "id": "xyz"}).encode()
    assert verify_necta_webhook_signature(tampered, headers, secret) is False


def test_verify_webhook_signature_rejects_expired_timestamp():
    secret = "whsec_" + base64.b64encode(b"super-secret-key").decode()
    body = json.dumps({"type": "sale.paid", "id": "abc"}).encode()
    old_timestamp = str(int(time.time()) - 3600)
    headers = {
        "svix-id": "msg_1",
        "svix-timestamp": old_timestamp,
        "svix-signature": sign(body, secret, "msg_1", old_timestamp),
    }
    assert verify_necta_webhook_signature(body, headers, secret) is False


def test_verify_webhook_signature_rejects_missing_headers():
    assert verify_necta_webhook_signature(b"{}", {}, "whsec_abc") is False