from __future__ import annotations

from celery import Celery

from app.config import Config


def _celery_redis_url(url: str) -> str:
    """Kombu/Celery require ssl_cert_reqs=CERT_NONE (not 'none'); redis-py uses 'none'."""
    if "rediss://" in url and "ssl_cert_reqs=none" in url:
        return url.replace("ssl_cert_reqs=none", "ssl_cert_reqs=CERT_NONE")
    return url


def make_celery() -> Celery:
    """Create and configure Celery application."""
    redis_url = _celery_redis_url(Config.REDIS_URL)

    celery = Celery(
        "papermind",
        broker=redis_url,
        backend=redis_url,
        include=[
            "app.tasks.ingestion_tasks",
            "app.tasks.embedding_tasks",
            "app.tasks.analysis_tasks",
        ],
    )

    # Reasonable defaults for early-stage production use
    celery.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    return celery


celery = make_celery()

