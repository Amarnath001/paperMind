"""Local embedding service using Sentence Transformers.

The model is loaded once (lazily on first use) and cached for the lifetime
of the process, so it is not reloaded on every request or Celery task.

Embeddings are generated entirely locally; to swap the embedding backend,
replace ``_load_model`` / ``_get_model`` while keeping the public interface —
``generate_embedding`` and ``generate_embeddings_batch`` — unchanged.
"""

from __future__ import annotations

import logging
from typing import List

from sentence_transformers import SentenceTransformer

from app.config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Private model cache
# ---------------------------------------------------------------------------

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the cached model, loading it on the first call."""
    global _model
    if _model is None:
        model_name = Config.EMBEDDING_MODEL
        logger.info("Loading embedding model '%s' …", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded.")
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_embedding(text: str) -> List[float]:
    """Return a normalised embedding vector for a single piece of text.

    Args:
        text: The input string to embed.

    Returns:
        A list of floats representing the embedding, ready for cosine
        similarity search (unit-normalised).
    """
    model = _get_model()
    vector = model.encode(
        text,
        normalize_embeddings=True,  # L2-normalise → cosine sim == dot product
        show_progress_bar=False,
    )
    return vector.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Return normalised embedding vectors for a batch of texts.

    Batching is significantly faster than calling ``generate_embedding``
    in a loop because the model can parallelise across the sequence axis.

    Args:
        texts: A list of input strings to embed.

    Returns:
        A list of embedding vectors in the same order as *texts*.
    """
    if not texts:
        return []

    model = _get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]
