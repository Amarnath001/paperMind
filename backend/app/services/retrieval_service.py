from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

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

    # 2) Search similar chunks in the workspace
    results = search_similar_chunks(workspace_id=workspace_id, query_embedding=query_embedding, limit=limit)

    if paper_id is not None:
        results = [r for r in results if str(r["paper_id"]) == str(paper_id)]

    return results[:limit]

