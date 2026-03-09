from __future__ import annotations

import os

from celery import Celery


def make_celery() -> Celery:
    """Create and configure Celery application."""
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    celery = Celery(
        "papermind",
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks.ingestion_tasks"],
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

