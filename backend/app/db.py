"""Database connection helpers."""

from __future__ import annotations

import contextlib
from typing import Iterator

import psycopg2
from flask import current_app


@contextlib.contextmanager
def get_db() -> Iterator[psycopg2.extensions.connection]:
    """Yield a new PostgreSQL connection using DATABASE_URL."""
    conn = psycopg2.connect(current_app.config["DATABASE_URL"])
    try:
        yield conn
    finally:
        conn.close()

