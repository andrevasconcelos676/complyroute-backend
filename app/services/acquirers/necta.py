"""Cliente de integração — Necta Multi-Pay.

Referência: https://doc.nectaco.com.br (OpenAPI 3.1, tag "Vendas").
Contrato genérico multi-gateway — a venda nasce sempre `pending` e o status
final definitivo chega por webhook (ver app/api/v1/endpoints/acquirers.py);
aqui tratamos apenas a resposta síncrona da criação/estorno.
"""

import base64
import hashlib
import hmac
import time
from typing import Any, Mapping

import httpx
import structlog

from app.core.exceptions import AcquirerError, AcquirerTimeoutError
from app.services.acquirers.base import AcquirerClient, SaleResult

log = structlog.get_logger()


def verify_necta_webhook_signature(
    payload: bytes,
    headers: Mapping[str, str],
    secret: str,
    tolerance_s: int = 300,
) -> bool:
    """
    Verifica a assinatura de um evento recebido em POST /acquirers/necta/webhook.

    Segue o esquema padrão Svix (usado pela Necta para os webhooks de saída):
    `svix-id`, `svix-timestamp` e `svix-signature` ("v1,<base64>", podendo ter
    mais de um valor espaço-separado durante rotação de segredo). O segredo
    tem o formato `whsec_<base64>`.
    """
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    if not svix_id or not svix_timestamp or not svix_signature or not secret:
        return False

    try:
        if abs(time.time() - int(svix_timestamp)) > tolerance_s:
            return False
    except ValueError:
        return False

    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed_content = f"{svix_id}.{svix_timestamp}.{payload.decode()}".encode()
    expected = base64.b64encode(hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()).decode()

    for candidate in svix_signature.split():
        _, _, sig = candidate.partition(",")
        if sig and hmac.compare_digest(sig, expected):
            return True
    return False

# Status da venda no Necta → status interno do ComplyRoute (txn_status)
_STATUS_MAP = {
    "pending": "processing",
    "processing": "processing",
    "scheduled": "processing",
    "pre_authorized": "processing",
    "paid": "approved",
    "refunded": "refunded",
    "partially_refunded": "refunded",
    "canceled": "declined",
    "denied": "declined",
    "refused": "declined",
    "expired": "declined",
}

_TOKEN_TTL_S = 25 * 60  # margem de segurança sob a expiração real do JWT (não documentada)


class NectaClient(AcquirerClient):
    """Cliente HTTP para a Necta Multi-Pay API (auth M2M + vendas em um passo)."""

    def __init__(
        self,
        client_secret: str,
        secret_key: str,
        base_url: str,
        http_client: httpx.AsyncClient | None = None,
        timeout_s: float = 10.0,
    ):
        if not client_secret or not secret_key:
            raise ValueError("NectaClient requer client_secret e secret_key.")
        self._client_secret = client_secret
        self._secret_key = secret_key
        self._http = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout_s)
        self._owns_http = http_client is None
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    # ── Autenticação ──────────────────────────────────────────

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        try:
            resp = await self._http.post(
                "/auth",
                json={"clientSecret": self._client_secret, "secretKey": self._secret_key},
            )
        except httpx.TimeoutException as e:
            raise AcquirerTimeoutError("necta") from e
        except httpx.HTTPError as e:
            raise AcquirerError("necta", f"Falha de conexão na autenticação: {e}") from e

        if resp.status_code != 200:
            raise AcquirerError("necta", f"Autenticação falhou (HTTP {resp.status_code}).")

        self._token = resp.json()["token"]
        self._token_expires_at = time.monotonic() + _TOKEN_TTL_S
        return self._token

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        token = await self._get_token()
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        resp = await self._do_request(method, path, headers, **kwargs)

        if resp.status_code == 401:
            # Token pode ter expirado antes do TTL local — reautentica uma vez.
            self._token = None
            headers["Authorization"] = f"Bearer {await self._get_token()}"
            resp = await self._do_request(method, path, headers, **kwargs)

        if resp.status_code >= 400:
            message = resp.text
            try:
                message = resp.json().get("message", message)
            except ValueError:
                pass
            raise AcquirerError("necta", f"HTTP {resp.status_code}: {message}")

        return resp

    async def _do_request(self, method: str, path: str, headers: dict, **kwargs) -> httpx.Response:
        try:
            return await self._http.request(method, path, headers=headers, **kwargs)
        except httpx.TimeoutException as e:
            raise AcquirerTimeoutError("necta") from e
        except httpx.HTTPError as e:
            raise AcquirerError("necta", f"Falha de conexão: {e}") from e

    # ── Vendas ────────────────────────────────────────────────

    async def create_sale(self, payload: Any) -> SaleResult:
        """
        Cria e processa uma venda em um passo, escolhendo o endpoint pelo
        método de pagamento (`payload.method`). `payload` é um
        `TransactionCreate` (app.schemas.transaction).
        """
        method = payload.method
        if method == "pix":
            path, body = "/sales/pix", self._pix_body(payload)
        elif method == "credit":
            path, body = "/sales/credit-card", self._credit_card_body(payload)
        elif method == "boleto":
            path, body = "/sales/bank-slip", self._bank_slip_body(payload)
        else:
            raise AcquirerError(
                "necta",
                f"Método '{method}' não suportado via venda em um passo (use pix, credit ou boleto).",
            )

        started = time.monotonic()
        resp = await self._request("POST", path, json=body)
        latency_ms = int((time.monotonic() - started) * 1000)

        data = resp.json()
        status_name = (data.get("status") or {}).get("name", "").lower()

        return SaleResult(
            status=_STATUS_MAP.get(status_name, "processing"),
            acquirer_txn_id=data.get("id"),
            authorization_code=data.get("externalId"),
            nsu=None,
            latency_ms=latency_ms,
            raw=data,
        )

    async def get_sale(self, sale_id: str) -> dict:
        resp = await self._request("GET", f"/sales/{sale_id}")
        return resp.json()

    async def refund_sale(self, acquirer_txn_id: str, amount: int | None = None) -> SaleResult:
        started = time.monotonic()
        body = {"amount": amount} if amount else None
        resp = await self._request("POST", f"/sales/{acquirer_txn_id}/void", json=body)
        latency_ms = int((time.monotonic() - started) * 1000)

        data = resp.json()
        return SaleResult(
            status=_STATUS_MAP.get((data.get("status") or "").lower(), "refunded"),
            acquirer_txn_id=data.get("id", acquirer_txn_id),
            authorization_code=None,
            nsu=None,
            latency_ms=latency_ms,
            raw=data,
        )

    # ── Montagem de payload ──────────────────────────────────

    @staticmethod
    def _buyer_body(payload: Any) -> dict:
        customer = payload.customer
        buyer: dict[str, Any] = {
            "name": customer.name,
            "document": customer.document,
            "email": customer.email,
            "phoneNumber": customer.phone_number or "00000000000",
        }
        if customer.address:
            addr = customer.address
            buyer["address"] = {
                "street": addr.street,
                "number": addr.number,
                "neighborhood": addr.neighborhood,
                "city": addr.city,
                "state": addr.state,
                "country": addr.country,
                "postalCode": addr.postal_code,
            }
        else:
            log.warning("necta.buyer_address_missing", customer_document=customer.document)
            buyer["address"] = {
                "street": "Não informado", "number": "S/N", "neighborhood": "Não informado",
                "city": "Não informado", "state": "SP", "country": "BR", "postalCode": "00000000",
            }
        return buyer

    def _pix_body(self, payload: Any) -> dict:
        return {
            "totalAmount": payload.amount,
            "liquidAmount": payload.amount,
            "buyer": self._buyer_body(payload),
        }

    def _credit_card_body(self, payload: Any) -> dict:
        if not payload.card:
            raise AcquirerError("necta", "Dados do cartão ausentes para pagamento em crédito.")
        card = payload.card
        month, _, year = card.expiry.partition("/")
        return {
            "totalAmount": payload.amount,
            "liquidAmount": payload.amount,
            "installments": payload.installments,
            "buyer": self._buyer_body(payload),
            "creditCard": {
                "holderName": card.holder,
                "number": card.number,
                "expirationMonth": month,
                "expirationYear": year,
                "cvv": card.cvv,
            },
        }

    def _bank_slip_body(self, payload: Any) -> dict:
        return {
            "totalAmount": payload.amount,
            "liquidAmount": payload.amount,
            "buyer": self._buyer_body(payload),
        }