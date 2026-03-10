from __future__ import annotations

from typing import Any, Dict, List

from sentence_transformers import CrossEncoder

from app.config import Config


_reranker_model: CrossEncoder | None = None


def _get_reranker_model() -> CrossEncoder:
    """Return the cached CrossEncoder model, loading it on first use."""
    global _reranker_model
    if _reranker_model is None:
        model_name = Config.RERANKER_MODEL
        _reranker_model = CrossEncoder(model_name)
    return _reranker_model


def rerank_chunks(
    question: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Rerank retrieved chunks using a local cross-encoder.

    Args:
        question: User question string.
        chunks:   List of chunk dicts (must include a ``text`` field).
        top_k:    Maximum number of chunks to return after reranking.

    Returns:
        A new list of chunk dicts sorted by rerank score (descending), each
        with an added ``rerank_score`` field. If there are fewer than top_k
        chunks, all are returned.
    """
    if not chunks:
        return []

    model = _get_reranker_model()

    # Build (question, chunk_text) pairs
    pairs: List[tuple[str, str]] = []
    for c in chunks:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        pairs.append((question, text))

    if not pairs:
        return chunks[:top_k]

    scores = model.predict(pairs)

    # Attach scores back to chunks in the same order as pairs
    scored_chunks: List[Dict[str, Any]] = []
    score_idx = 0
    for c in chunks:
        text = (c.get("text") or "").strip()
        if not text:
            # chunks without text get the lowest possible score
            c_with_score = dict(c)
            c_with_score["rerank_score"] = float("-inf")
            scored_chunks.append(c_with_score)
            continue
        c_with_score = dict(c)
        c_with_score["rerank_score"] = float(scores[score_idx])
        scored_chunks.append(c_with_score)
        score_idx += 1

    scored_chunks.sort(key=lambda x: x.get("rerank_score", float("-inf")), reverse=True)
    return scored_chunks[:top_k]

