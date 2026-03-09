from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import bcrypt
import jwt
from flask import current_app, g, request

from app.db import get_db


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(user_id: UUID) -> str:
    now = dt.datetime.now(tz=dt.timezone.utc)
    expires = now + dt.timedelta(
        minutes=current_app.config["ACCESS_TOKEN_EXPIRES_MINUTES"]
    )
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    return token


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=[current_app.config["JWT_ALGORITHM"]],
    )


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = %s",
                (email.lower(),),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3],
    }


def get_user_by_id(user_id: UUID) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id = %s",
                (str(user_id),),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3],
    }


def create_user(email: str, password: str) -> Dict[str, Any]:
    user_id = uuid4()
    password_hash = hash_password(password)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, email, password_hash, created_at
                """,
                (str(user_id), email.lower(), password_hash),
            )
            row = cur.fetchone()
        conn.commit()
    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "created_at": row[3],
    }


def _get_token_from_header() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip() or None


def require_auth() -> Dict[str, Any]:
    """Decode JWT and load current user; raise ValueError on failure."""
    token = _get_token_from_header()
    if not token:
        raise ValueError("Missing or invalid Authorization header")

    data = decode_token(token)
    user_id = data.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload")

    user = get_user_by_id(UUID(user_id))
    if not user:
        raise ValueError("User not found")

    g.current_user = user
    return user


def get_current_user() -> Optional[Dict[str, Any]]:
    return getattr(g, "current_user", None)

