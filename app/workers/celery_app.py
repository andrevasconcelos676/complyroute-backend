"""Configuração do Celery — filas assíncronas."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "complyroute",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.webhooks",
        "app.workers.tasks.reconciliation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Conciliação diária às 06h
        "daily-reconciliation": {
            "task": "app.workers.tasks.reconciliation.run_daily_reconciliation",
            "schedule": 21600.0,   # 6h em segundos
        },
    },
)
