"""Exceções customizadas e registro de handlers no FastAPI."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ── Exceções de domínio ───────────────────────────────────

class ComplyRouteException(Exception):
    """Base de todas as exceções da aplicação."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ComplyRouteException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} '{identifier}' não encontrado.", "NOT_FOUND", 404)


class ValidationError(ComplyRouteException):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 422)


class AuthenticationError(ComplyRouteException):
    def __init__(self, message: str = "Credenciais inválidas."):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(ComplyRouteException):
    def __init__(self, message: str = "Acesso negado."):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class AcquirerError(ComplyRouteException):
    def __init__(self, acquirer: str, message: str):
        super().__init__(f"Erro no subadquirente {acquirer}: {message}", "ACQUIRER_ERROR", 502)


class AcquirerTimeoutError(ComplyRouteException):
    def __init__(self, acquirer: str):
        super().__init__(f"Timeout ao conectar com {acquirer}.", "ACQUIRER_TIMEOUT", 504)


class FraudBlockError(ComplyRouteException):
    def __init__(self, score: int):
        super().__init__(f"Transação bloqueada por antifraude (score: {score}).", "FRAUD_BLOCKED", 422)


class RoutingError(ComplyRouteException):
    def __init__(self, message: str):
        super().__init__(message, "ROUTING_ERROR", 422)


class RateLimitError(ComplyRouteException):
    def __init__(self):
        super().__init__("Limite de requisições atingido. Tente novamente em instantes.", "RATE_LIMIT", 429)


# ── Registro dos handlers ─────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(ComplyRouteException)
    async def complyroute_handler(request: Request, exc: ComplyRouteException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "NOT_FOUND", "message": "Recurso não encontrado."},
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "INTERNAL_ERROR", "message": "Erro interno do servidor."},
        )
