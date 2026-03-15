"""Application configuration."""

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_redis_url(url: str) -> str:
    """Add ssl_cert_reqs=none to rediss:// URLs for redis-py (Flask-Limiter, health). Celery needs CERT_NONE and is handled in celery_app."""
    if not url.startswith("rediss://"):
        return url
    parsed = urlparse(url)
    qs = dict(parse_qsl(parsed.query))
    if "ssl_cert_reqs" not in qs:
        qs["ssl_cert_reqs"] = "none"  # redis-py expects lowercase "none"
    return urlunparse(parsed._replace(query=urlencode(qs)))


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # CORS: allowed origins (set CORS_ORIGINS env to override; include your exact Vercel URL)
    _default_origins = (
        "https://paper-mind-six.vercel.app,"
        "https://paper-mind-pla.vercel.app,"
        "https://paper-mind.vercel.app,"
        "http://localhost:3000"
    )
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", _default_origins).strip().split(",")
    CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS if o.strip()]

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRES_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRES_MINUTES", "60"))

    # File uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

    # Database
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/papermind",
    )

    # Redis (rediss:// URLs normalized with ssl_cert_reqs for Celery/redis clients)
    REDIS_URL = _normalize_redis_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    )

    # Embeddings (gemini for lightweight deploy; local sentence-transformers optional)
    EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "gemini")
    EMBEDDING_MODEL = os.environ.get(
        "EMBEDDING_MODEL", "models/text-embedding-004"
    )
    EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "384"))

    # Lightweight deployment (Railway/Vercel/Render): no worker, no local ML
    LIGHTWEIGHT_DEPLOYMENT = os.environ.get("LIGHTWEIGHT_DEPLOYMENT", "true").lower() in {
        "1", "true", "yes",
    }
    ASYNC_PROCESSING = os.environ.get("ASYNC_PROCESSING", "false").lower() in {
        "1", "true", "yes",
    }
    ENABLE_LOCAL_RERANKING = os.environ.get("ENABLE_LOCAL_RERANKING", "false").lower() in {
        "1", "true", "yes",
    }
    ENABLE_CLUSTERING = os.environ.get("ENABLE_CLUSTERING", "false").lower() in {
        "1", "true", "yes",
    }

    # LLMs
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

    # Storage (for Cloudflare R2 set STORAGE_PROVIDER=s3 and S3_REGION=auto)
    STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "local")  # local | s3
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "")
    S3_REGION = os.environ.get("S3_REGION") or (
        "auto" if os.environ.get("S3_ENDPOINT_URL") else ""
    )
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")

    # Retrieval / reranking (local cross-encoder; disabled in lightweight mode)
    RERANKER_MODEL = os.environ.get(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    ENABLE_RERANKING = os.environ.get("ENABLE_RERANKING", "false").lower() in {
        "1", "true", "yes",
    }
    INITIAL_RETRIEVAL_LIMIT = int(os.environ.get("INITIAL_RETRIEVAL_LIMIT", "20"))
    FINAL_CONTEXT_LIMIT = int(os.environ.get("FINAL_CONTEXT_LIMIT", "5"))
