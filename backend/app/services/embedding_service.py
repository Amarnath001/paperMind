"""Embedding service: Gemini API for production; optional local model for dev.

When EMBEDDING_PROVIDER=gemini (default), uses Google Generative AI to produce
384-d vectors. No sentence-transformers or torch required, so the backend stays
lightweight for Railway/Vercel/Render.
"""

from __future__ import annotations

import logging
from typing import List

from app.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini embedding (no local ML deps)
# ---------------------------------------------------------------------------


def _configure_gemini_embedding() -> None:
    import google.generativeai as genai

    if not Config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini. "
            "Set it in your environment or .env."
        )
    genai.configure(api_key=Config.GEMINI_API_KEY)


def _gemini_embed_one(text: str) -> List[float]:
    """Return a single normalised embedding from the Gemini API."""
    import google.generativeai as genai

    model = Config.EMBEDDING_MODEL
    dim = Config.EMBEDDING_DIMENSION

    result = genai.embed_content(
        model=model,
        content=text.strip() or " ",
        output_dimensionality=dim,
    )

    # Response shape: {'embedding': [float, ...]} or object with .embedding
    if isinstance(result, dict):
        embedding = result.get("embedding")
    else:
        embedding = getattr(result, "embedding", None)
    if embedding is None and isinstance(result, (list, tuple)):
        embedding = result
    if embedding is None:
        raise RuntimeError("Gemini embed_content did not return an embedding")

    vec = list(embedding)

    # Truncate or pad to EMBEDDING_DIMENSION for DB (384)
    if len(vec) > dim:
        vec = vec[:dim]
    elif len(vec) < dim:
        vec = vec + [0.0] * (dim - len(vec))

    # L2-normalise for cosine similarity
    mag = sum(x * x for x in vec) ** 0.5
    if mag > 0:
        vec = [x / mag for x in vec]
    return vec


def generate_embedding(text: str) -> List[float]:
    """Return a normalised embedding vector for a single piece of text.

    Uses the configured EMBEDDING_PROVIDER (gemini by default). Output length
    matches EMBEDDING_DIMENSION (384) for pgvector compatibility.
    """
    provider = (Config.EMBEDDING_PROVIDER or "gemini").lower()
    if provider == "gemini":
        _configure_gemini_embedding()
        return _gemini_embed_one(text)
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider!r}. Use gemini.")


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Return normalised embedding vectors for a batch of texts.

    With Gemini we call the API per text (or in small batches if the SDK
    supports it) to avoid token limits and keep the implementation simple.
    """
    if not texts:
        return []

    provider = (Config.EMBEDDING_PROVIDER or "gemini").lower()
    if provider == "gemini":
        _configure_gemini_embedding()
        return [_gemini_embed_one(t) for t in texts]
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider!r}. Use gemini.")
