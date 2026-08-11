"""Fábrica de clientes de subadquirente — resolve pelo nome usado no roteamento."""

from app.core.config import settings
from app.services.acquirers.base import AcquirerClient
from app.services.acquirers.necta import NectaClient


class AcquirerClientFactory:
    """
    Resolve o cliente real de um subadquirente pelo nome (`Acquirer.name` /
    `RoutingDecision.acquirer`). Retorna `None` quando não há integração real
    implementada ou credenciais configuradas — o caller deve tratar isso como
    "sem integração disponível" (o restante da plataforma ainda opera em modo
    simulado para os demais subadquirentes).
    """

    @staticmethod
    def get(name: str) -> AcquirerClient | None:
        if name == "necta":
            if not settings.NECTA_CLIENT_SECRET or not settings.NECTA_SECRET_KEY:
                return None
            return NectaClient(
                client_secret=settings.NECTA_CLIENT_SECRET,
                secret_key=settings.NECTA_SECRET_KEY,
                base_url=settings.NECTA_API_URL,
            )
        return None