"""Database connection helpers."""

from __future__ import annotations

import contextlib
from typing import Iterator

import psycopg2

from app.config import Config


@contextlib.contextmanager
def get_db() -> Iterator[psycopg2.extensions.connection]:
    """Yield a new PostgreSQL connection using DATABASE_URL.

    This helper intentionally avoids depending on Flask's ``current_app`` so
    that it can be used safely from both request handlers and background
    Celery workers.
    """
    conn = psycopg2.connect(Config.DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

