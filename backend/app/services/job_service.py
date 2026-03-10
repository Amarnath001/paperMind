from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID, uuid4

from app.db import get_db


def create_job(
    workspace_id: UUID,
    paper_id: Optional[UUID],
    job_type: str,
    status: str = "queued",
    progress: int = 0,
) -> Dict[str, Any]:
    job_id = uuid4()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs (
                    id, workspace_id, paper_id, type, status, progress,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id, workspace_id, paper_id, type, status, progress, error, created_at, updated_at
                """,
                (str(job_id), str(workspace_id), str(paper_id) if paper_id else None, job_type, status, progress),
            )
            row = cur.fetchone()
        conn.commit()

    return _row_to_job_dict(row)


def update_job_status(job_id: UUID, status: str, progress: Optional[int] = None, error: Optional[str] = None) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            fields = ["status = %s", "updated_at = NOW()"]
            params: List[Any] = [status]
            if progress is not None:
                fields.append("progress = %s")
                params.append(progress)
            if error is not None:
                fields.append("error = %s")
                params.append(error)

            params.append(str(job_id))
            cur.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE id = %s",
                params,
            )
        conn.commit()


def mark_job_failed(job_id: UUID, error_message: str) -> None:
    update_job_status(job_id, status="failed", error=error_message)


def set_paper_status(paper_id: UUID, status: str) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE papers
                SET status = %s
                WHERE id = %s
                """,
                (status, str(paper_id)),
            )
        conn.commit()


def delete_chunks_for_paper(paper_id: UUID) -> None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE paper_id = %s", (str(paper_id),))
        conn.commit()


def insert_chunks(
    paper_id: UUID,
    chunks: Iterable[tuple[int, str, int]],
) -> None:
    now = datetime.now(timezone.utc)
    with get_db() as conn:
        with conn.cursor() as cur:
            for index, text, token_count in chunks:
                chunk_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO chunks (id, paper_id, chunk_index, text, token_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (str(chunk_id), str(paper_id), index, text, token_count, now),
                )
        conn.commit()


def _row_to_job_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": row[0],
        "workspace_id": row[1],
        "paper_id": row[2],
        "type": row[3],
        "status": row[4],
        "progress": row[5],
        "error": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }


def get_chunks_for_paper(paper_id: UUID) -> List[Dict[str, Any]]:
    """Return all chunks for *paper_id* ordered by chunk_index."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, paper_id, chunk_index, text, token_count, created_at
                FROM   chunks
                WHERE  paper_id = %s
                ORDER  BY chunk_index
                """,
                (str(paper_id),),
            )
            rows = cur.fetchall()
    return [
        {
            "id": row[0],
            "paper_id": row[1],
            "chunk_index": row[2],
            "text": row[3],
            "token_count": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def has_pending_embedding_job(paper_id: UUID) -> bool:
    """Return True if an active (queued/running) embedding job already exists.

    Used to prevent duplicate embedding jobs being queued on retries or
    re-ingestion runs.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM jobs
                WHERE  paper_id = %s
                  AND  type     = 'embedding'
                  AND  status   IN ('queued', 'running')
                LIMIT 1
                """,
                (str(paper_id),),
            )
            return cur.fetchone() is not None

