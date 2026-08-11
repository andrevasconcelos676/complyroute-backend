"""
Smoke test manual — Necta Multi-Pay.

Valida o NectaClient direto contra a API real (sandbox ou produção, conforme
NECTA_API_URL/credenciais no .env), sem passar pelo resto do ComplyRoute.

Uso:
    python scripts/necta_smoke_test.py                  # cria venda PIX de R$ 5,00
    python scripts/necta_smoke_test.py --amount 1000     # valor customizado (centavos)
    python scripts/necta_smoke_test.py --refund <uuid>   # estorna uma venda já criada

Requer NECTA_CLIENT_SECRET e NECTA_SECRET_KEY configurados no .env
(gerados em POST /api-tokens no painel Necta).
"""

import argparse
import asyncio
import sys

from app.core.config import settings
from app.schemas.transaction import CustomerAddress, CustomerData, TransactionCreate
from app.services.acquirers.necta import NectaClient


async def create_pix_sale(client: NectaClient, amount: int) -> None:
    payload = TransactionCreate(
        amount=amount,
        method="pix",
        customer=CustomerData(
            name="Comprador Teste",
            document="12345678909",
            email="teste@complyroute.com.br",
            phone_number="11999998888",
            address=CustomerAddress(
                street="Av. Paulista", number="1000", neighborhood="Bela Vista",
                city="São Paulo", state="SP", postal_code="01310100", country="BR",
            ),
        ),
    )
    print(f"Criando venda PIX de R$ {amount / 100:.2f}...")
    result = await client.create_sale(payload)
    print(f"  status (ComplyRoute)....: {result.status}")
    print(f"  id da venda (Necta).....: {result.acquirer_txn_id}")
    print(f"  externalId (gateway)....: {result.authorization_code}")
    print(f"  latência.................: {result.latency_ms}ms")
    print(f"  payload bruto............: {result.raw}")

    detail = await client.get_sale(result.acquirer_txn_id)
    qr_code = detail.get("qrCode")
    if qr_code:
        print(f"  QR Code (copia-e-cola)...: {qr_code}")


async def refund_sale(client: NectaClient, sale_id: str) -> None:
    print(f"Estornando venda {sale_id}...")
    result = await client.refund_sale(sale_id)
    print(f"  status: {result.status}")
    print(f"  raw...: {result.raw}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amount", type=int, default=500, help="Valor em centavos (default: 500 = R$5,00)")
    parser.add_argument("--refund", metavar="SALE_UUID", help="Estorna uma venda existente em vez de criar uma nova")
    args = parser.parse_args()

    if not settings.NECTA_CLIENT_SECRET or not settings.NECTA_SECRET_KEY:
        print("Erro: configure NECTA_CLIENT_SECRET e NECTA_SECRET_KEY no .env antes de rodar.", file=sys.stderr)
        sys.exit(1)

    client = NectaClient(
        client_secret=settings.NECTA_CLIENT_SECRET,
        secret_key=settings.NECTA_SECRET_KEY,
        base_url=settings.NECTA_API_URL,
    )
    try:
        if args.refund:
            await refund_sale(client, args.refund)
        else:
            await create_pix_sale(client, args.amount)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())