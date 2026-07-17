"""
ComplyRoute — Gateway de Pagamento
Entry point da aplicação FastAPI.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.endpoints import (
    auth,
    transactions,
    routing,
    acquirers,
    webhooks,
    users,
    reconciliation,
    settings,
)
from app.core.config import settings as cfg
from app.core.exceptions import AuthenticationError, ComplyRouteException, register_exception_handlers
from app.core.logging import configure_logging
from app.core.security import decode_token
from fastapi.responses import FileResponse, JSONResponse
from app.db.session import engine
from app.db.base import Base, import_all_models

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação."""
    configure_logging()
    log.info("complyroute.starting", version=cfg.APP_VERSION, env=cfg.APP_ENV)

    # Em modo local, não tentamos criar o banco na startup para evitar problemas de driver/compatibilidade.
    if cfg.APP_ENV == "development":
        import_all_models()

    log.info("complyroute.ready")
    yield
    log.info("complyroute.shutdown")
    await engine.dispose()


app = FastAPI(
    title="ComplyRoute API",
    description="Gateway de Pagamento com roteamento inteligente — COMPLYSOFT DESENVOLVIMENTO DE SISTEMAS LTDA",
    version=cfg.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/dashboard",
    "/dashboard/",
}


def _auth_error_response(exc: ComplyRouteException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})


@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    """Protege todos os endpoints, exceto login, refresh, health e documentação.

    Este middleware roda fora do ExceptionMiddleware do Starlette, então exceções
    levantadas aqui nunca chegariam aos handlers de register_exception_handlers —
    por isso a resposta de erro é montada e retornada diretamente aqui.
    """
    path = request.url.path

    if request.method == "OPTIONS" or path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        return await call_next(request)

    if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/refresh"):
        return await call_next(request)

    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return _auth_error_response(AuthenticationError("Token de acesso ausente."))

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return _auth_error_response(AuthenticationError("Token de acesso ausente."))

    try:
        payload = decode_token(token)
    except Exception:
        return _auth_error_response(AuthenticationError("Token inválido ou expirado."))

    if payload.get("type") != "access":
        return _auth_error_response(AuthenticationError("Token inválido."))

    request.state.user = payload
    request.state.user_id = payload.get("sub")
    return await call_next(request)


# ── Middlewares ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if cfg.APP_ENV == "development" else cfg.allowed_hosts_list,
)

# ── Prometheus metrics ─────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Exception handlers ─────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router,           prefix=f"{PREFIX}/auth",           tags=["Autenticação"])
app.include_router(transactions.router,   prefix=f"{PREFIX}/transactions",   tags=["Transações"])
app.include_router(routing.router,        prefix=f"{PREFIX}/routing",        tags=["Roteamento"])
app.include_router(acquirers.router,      prefix=f"{PREFIX}/acquirers",      tags=["Subadquirentes"])
app.include_router(webhooks.router,       prefix=f"{PREFIX}/webhooks",       tags=["Webhooks"])
app.include_router(users.router,          prefix=f"{PREFIX}/users",          tags=["Usuários"])
app.include_router(reconciliation.router, prefix=f"{PREFIX}/reconciliation", tags=["Conciliação"])
app.include_router(settings.router,       prefix=f"{PREFIX}/settings",       tags=["Configurações"])


@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    dashboard_path = Path(__file__).resolve().parent / "app" / "static" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path, media_type="text/html")
    return {"service": "ComplyRoute API", "version": cfg.APP_VERSION, "status": "operational"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": cfg.APP_VERSION, "env": cfg.APP_ENV}


@app.get("/dashboard", include_in_schema=False)
@app.get("/dashboard/", include_in_schema=False)
async def dashboard():
    dashboard_path = Path(__file__).resolve().parent / "app" / "static" / "dashboard.html"
    if not dashboard_path.exists():
        return {"error": "Dashboard file not found", "path": str(dashboard_path)}
    return FileResponse(dashboard_path, media_type="text/html")
