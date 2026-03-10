"""Application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

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

    # Redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # OpenAI (for future use)
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Embeddings
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "384"))

    # LLMs
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

    # Retrieval / reranking
    RERANKER_MODEL = os.environ.get(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    ENABLE_RERANKING = os.environ.get("ENABLE_RERANKING", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    INITIAL_RETRIEVAL_LIMIT = int(os.environ.get("INITIAL_RETRIEVAL_LIMIT", "20"))
    FINAL_CONTEXT_LIMIT = int(os.environ.get("FINAL_CONTEXT_LIMIT", "5"))
