from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.config import Config
from app.services.embedding_service import generate_embedding
from app.services.vector_service import search_similar_chunks


def retrieve_context_for_question(
    workspace_id: UUID,
    question: str,
    limit: int = 8,
    paper_id: Optional[UUID] = None,
) -> List[Dict[str, Any]]:
    """Retrieve the most relevant chunks for a question within a workspace.

    Args:
        workspace_id: Scope retrieval to this workspace.
        question:     Natural language question from the user.
        limit:        Maximum number of chunks to return (default: 8).
        paper_id:     Optional paper to restrict retrieval to. When provided,
                      only chunks from this paper are returned.
    """
    if not question.strip():
        return []

    # 1) Embed the question using the local Sentence Transformers model
    query_embedding = generate_embedding(question)

    # 2) Initial retrieval using pgvector with a broader candidate set
    initial_limit = max(limit, Config.INITIAL_RETRIEVAL_LIMIT)
    candidates = search_similar_chunks(
        workspace_id=workspace_id,
        query_embedding=query_embedding,
        limit=initial_limit,
    )

    if paper_id is not None:
        candidates = [r for r in candidates if str(r["paper_id"]) == str(paper_id)]

    final_limit = min(limit, Config.FINAL_CONTEXT_LIMIT)

    if not candidates:
        return []

    # 3) Optional local reranking (skip in lightweight deploy; no cross-encoder)
    if Config.ENABLE_RERANKING:
        from app.services.reranking_service import rerank_chunks

        reranked = rerank_chunks(question, candidates, top_k=final_limit)
        return reranked

    return candidates[:final_limit]

