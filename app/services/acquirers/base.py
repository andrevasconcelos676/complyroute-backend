"""Interface comum dos clientes de subadquirente."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SaleResult:
    """Resultado normalizado de uma operação no gateway — formato consumido por transactions.py."""
    status: str                    # approved | processing | declined | refunded
    acquirer_txn_id: str | None    # id público da venda no gateway
    authorization_code: str | None
    nsu: str | None
    latency_ms: int
    raw: dict[str, Any]


class AcquirerClient(ABC):
    """Cliente de integração com um subadquirente real."""

    @abstractmethod
    async def create_sale(self, payload: Any) -> SaleResult:
        ...

    @abstractmethod
    async def refund_sale(self, acquirer_txn_id: str, amount: int | None = None) -> SaleResult:
        ...