"""Vector database helper functions for pgvector similarity search.

All functions use explicit SQL via psycopg2 and the pgvector ``<=>`` operator
(cosine distance).  Results include a ``similarity`` field in [0, 1] computed
as ``1 - cosine_distance``.

Multi-tenancy is enforced by joining ``chunks → papers → workspaces`` so that
every search is automatically scoped to a single workspace.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.db import get_db


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _embedding_literal(embedding: List[float]) -> str:
    """Serialise a Python float list to the pgvector literal format.

    pgvector accepts embeddings as a string of the form ``'[0.1,0.2,...]'``
    when cast to ``vector`` in SQL.
    """
    return "[" + ",".join(str(v) for v in embedding) + "]"


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def save_chunk_embedding(chunk_id: UUID, embedding: List[float]) -> None:
    """Persist an embedding vector for a single chunk row.

    Args:
        chunk_id:  The UUID of the chunk to update.
        embedding: A normalised float list of length 384.
    """
    literal = _embedding_literal(embedding)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE chunks
                SET    embedding = %s::vector
                WHERE  id = %s
                """,
                (literal, str(chunk_id)),
            )
        conn.commit()


def save_paper_embedding(paper_id: UUID, embedding: List[float]) -> None:
    """Persist an embedding vector for a single paper row.

    Args:
        paper_id:  The UUID of the paper to update.
        embedding: A normalised float list of length 384.
    """
    literal = _embedding_literal(embedding)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE papers
                SET    embedding = %s::vector
                WHERE  id = %s
                """,
                (literal, str(paper_id)),
            )
        conn.commit()


# ---------------------------------------------------------------------------
# Read / search helpers
# ---------------------------------------------------------------------------


def search_similar_chunks(
    workspace_id: UUID,
    query_embedding: List[float],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Find the most similar chunks within a workspace.

    Performs a cosine-distance search over ``chunks.embedding``, restricted to
    chunks that belong to papers in *workspace_id*.

    Args:
        workspace_id:    Only return chunks from this workspace.
        query_embedding: The query vector (should be normalised, length 384).
        limit:           Maximum number of results to return.

    Returns:
        A list of dicts with keys:
            - ``chunk_id``    – UUID of the matching chunk
            - ``paper_id``    – UUID of the parent paper
            - ``paper_title`` – string title of the parent paper
            - ``chunk_index`` – position of the chunk inside its paper
            - ``text``        – raw chunk text
            - ``token_count`` – token count (may be None)
            - ``similarity``  – float in [0, 1]; higher means more similar
    """
    literal = _embedding_literal(query_embedding)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.id            AS chunk_id,
                    c.paper_id,
                    p.title         AS paper_title,
                    c.chunk_index,
                    c.text,
                    c.token_count,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM  chunks  c
                JOIN  papers  p ON p.id = c.paper_id
                WHERE p.workspace_id = %s
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (literal, str(workspace_id), literal, limit),
            )
            rows = cur.fetchall()

    return [_row_to_chunk_result(row) for row in rows]


def search_similar_papers(
    workspace_id: UUID,
    paper_id: Optional[UUID] = None,
    embedding: Optional[List[float]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Find papers within a workspace that are similar to a given vector.

    Exactly one of *paper_id* or *embedding* must be supplied:

    - Pass ``paper_id`` to find papers similar to an already-ingested paper.
    - Pass ``embedding`` to search with an arbitrary query vector.

    When *paper_id* is given the paper itself is excluded from the results.

    Args:
        workspace_id: Only return papers from this workspace.
        paper_id:     Optional — source paper to compare against.
        embedding:    Optional — explicit query vector (normalised, length 384).
        limit:        Maximum number of results to return.

    Returns:
        A list of dicts with keys:
            - ``paper_id``   – UUID of the matching paper
            - ``title``      – paper title
            - ``status``     – paper status
            - ``similarity`` – float in [0, 1]; higher means more similar

    Raises:
        ValueError: If neither or both of *paper_id* and *embedding* are given.
    """
    if (paper_id is None) == (embedding is None):
        raise ValueError(
            "Provide exactly one of 'paper_id' or 'embedding', not both or neither."
        )

    # Resolve the query vector
    if paper_id is not None:
        query_literal = _resolve_paper_embedding_literal(paper_id)
    else:
        query_literal = _embedding_literal(embedding)  # type: ignore[arg-type]

    with get_db() as conn:
        with conn.cursor() as cur:
            if paper_id is not None:
                cur.execute(
                    """
                    SELECT
                        p.id    AS paper_id,
                        p.title,
                        p.status,
                        1 - (p.embedding <=> %s::vector) AS similarity
                    FROM  papers p
                    WHERE p.workspace_id = %s
                      AND p.id          != %s
                      AND p.embedding   IS NOT NULL
                    ORDER BY p.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        query_literal,
                        str(workspace_id),
                        str(paper_id),
                        query_literal,
                        limit,
                    ),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        p.id    AS paper_id,
                        p.title,
                        p.status,
                        1 - (p.embedding <=> %s::vector) AS similarity
                    FROM  papers p
                    WHERE p.workspace_id = %s
                      AND p.embedding   IS NOT NULL
                    ORDER BY p.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (query_literal, str(workspace_id), query_literal, limit),
                )
            rows = cur.fetchall()

    return [_row_to_paper_result(row) for row in rows]


# ---------------------------------------------------------------------------
# Private row mappers
# ---------------------------------------------------------------------------


def _resolve_paper_embedding_literal(paper_id: UUID) -> str:
    """Fetch the stored embedding for *paper_id* and return its literal form."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT embedding FROM papers WHERE id = %s",
                (str(paper_id),),
            )
            row = cur.fetchone()

    if row is None or row[0] is None:
        raise ValueError(f"Paper {paper_id} has no stored embedding.")

    # psycopg2 returns pgvector values as a string already; pass it through.
    return row[0]


def _row_to_chunk_result(row: Any) -> Dict[str, Any]:
    return {
        "chunk_id": row[0],
        "paper_id": row[1],
        "paper_title": row[2],
        "chunk_index": row[3],
        "text": row[4],
        "token_count": row[5],
        "similarity": float(row[6]),
    }


def _row_to_paper_result(row: Any) -> Dict[str, Any]:
    return {
        "paper_id": row[0],
        "title": row[1],
        "status": row[2],
        "similarity": float(row[3]),
    }
