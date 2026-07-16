"""Endpoints de Configurações — /api/v1/settings"""

from fastapi import APIRouter
from app.core.config import settings as cfg

router = APIRouter()


@router.get("")
async def get_settings():
    """Retorna configurações públicas (não expostas: secrets, chaves de API)."""
    return {
        "app_name": cfg.APP_NAME,
        "app_version": cfg.APP_VERSION,
        "app_env": cfg.APP_ENV,
        "fraud_score_min_auto_approve": cfg.FRAUD_SCORE_MIN_AUTO_APPROVE,
        "fraud_score_min_manual_review": cfg.FRAUD_SCORE_MIN_MANUAL_REVIEW,
        "txn_min_amount": cfg.TXN_MIN_AMOUNT,
        "txn_max_amount": cfg.TXN_MAX_AMOUNT,
        "txn_max_installments": cfg.TXN_MAX_INSTALLMENTS,
        "txn_timeout_ms": cfg.TXN_TIMEOUT_MS,
        "txn_max_retries": cfg.TXN_MAX_RETRIES,
    }
