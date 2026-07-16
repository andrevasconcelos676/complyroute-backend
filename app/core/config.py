"""Configurações da aplicação via variáveis de ambiente."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ────────────────────────────────────────
    APP_NAME: str = "ComplyRoute"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-change-me"
    # Strings simples (não List[str]) para evitar que o pydantic-settings tente
    # fazer JSON.parse do valor da env var — aceitam lista separada por vírgula.
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    ALLOWED_HOSTS: str = "*"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    # ── Database (local SQLite by default) ────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./complyroute.db"
    DATABASE_URL_SYNC: str = "sqlite:///./complyroute.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis / Celery ─────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── JWT ────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Webhook ────────────────────────────────────
    WEBHOOK_SECRET: str = ""

    # ── Antifraude ─────────────────────────────────
    FRAUD_SCORE_MIN_AUTO_APPROVE: int = 70
    FRAUD_SCORE_MIN_MANUAL_REVIEW: int = 50

    # ── Limites Operacionais ───────────────────────
    TXN_MIN_AMOUNT: int = 100           # centavos
    TXN_MAX_AMOUNT: int = 5_000_000    # centavos
    TXN_MAX_INSTALLMENTS: int = 18
    TXN_TIMEOUT_MS: int = 5000
    TXN_MAX_RETRIES: int = 3

    # ── Subadquirentes ─────────────────────────────
    CIELO_MERCHANT_ID: str = ""
    CIELO_MERCHANT_KEY: str = ""
    CIELO_API_URL: str = "https://api.cieloecommerce.cielo.com.br"

    REDE_PV: str = ""
    REDE_TOKEN: str = ""
    REDE_API_URL: str = "https://api.userede.com.br"

    STONE_CLIENT_ID: str = ""
    STONE_CLIENT_SECRET: str = ""
    STONE_API_URL: str = "https://api.openbank.stone.com.br"

    PAGSEGURO_TOKEN: str = ""
    PAGSEGURO_API_URL: str = "https://api.pagseguro.com"

    GETNET_CLIENT_ID: str = ""
    GETNET_CLIENT_SECRET: str = ""
    GETNET_API_URL: str = "https://api.getnet.com.br"

    SAFRAPAY_API_KEY: str = ""
    SAFRAPAY_API_URL: str = "https://api.safrapay.com.br"

    ZOOP_MARKETPLACE_ID: str = ""
    ZOOP_API_KEY: str = ""
    ZOOP_API_URL: str = "https://api.zoop.ws"

    ASAAS_API_KEY: str = ""
    ASAAS_API_URL: str = "https://api.asaas.com/v3"

    ORENDAPAY_CLIENT_ID: str = ""
    ORENDAPAY_CLIENT_SECRET: str = ""
    ORENDAPAY_API_URL: str = "https://api.orendapay.com.br"

    # ── Observability ──────────────────────────────
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
