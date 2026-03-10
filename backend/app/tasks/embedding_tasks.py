"""Celery task: generate and store embeddings for an ingested paper.

Pipeline
--------
1. Mark job running.
2. Load all chunks for the paper (ordered by chunk_index).
3. Batch-encode chunk texts with the local sentence-transformer model.
4. Save each chunk embedding to the database.
5. Compute a paper-level embedding by averaging the chunk vectors.
6. Save the paper embedding.
7. Mark the embedding job completed (progress = 100).
8. Mark the paper status = 'ready'.

On error the job and paper are both marked failed, and the exception is
re-raised so Celery records the failure correctly.

Idempotency
-----------
Embeddings are stored via UPDATE — re-running the task overwrites existing
vectors cleanly without duplicating rows.  The upstream ingestion task only
queues this task when no active embedding job already exists for the paper
(see ``has_pending_embedding_job`` in job_service).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from app.celery_app import celery
from app.services.embedding_service import generate_embeddings_batch
from app.services.job_service import (
    create_job,
    get_chunks_for_paper,
    mark_job_failed,
    set_paper_status,
    update_job_status,
)
from app.services.vector_service import save_chunk_embedding, save_paper_embedding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@celery.task(bind=True, name="app.tasks.embed_paper")
def embed_paper_task(
    self: Any,
    job_id: str,
    paper_id: str,
    workspace_id: str,
) -> Dict[str, Any]:
    """Generate and store embeddings for all chunks and the paper itself.

    Args:
        job_id:       UUID string of the embedding job row.
        paper_id:     UUID string of the paper to embed.
        workspace_id: UUID string of the owning workspace (logged / reserved).
    """
    job_uuid = UUID(job_id)
    paper_uuid = UUID(paper_id)

    logger.info(
        "Starting embedding task | job=%s paper=%s workspace=%s",
        job_id,
        paper_id,
        workspace_id,
    )

    try:
        # ------------------------------------------------------------------ #
        # 1. Mark job as running
        # ------------------------------------------------------------------ #
        update_job_status(job_uuid, status="running", progress=0)

        # ------------------------------------------------------------------ #
        # 2. Load chunks
        # ------------------------------------------------------------------ #
        chunks = get_chunks_for_paper(paper_uuid)
        if not chunks:
            raise ValueError(f"No chunks found for paper {paper_id}. Cannot embed.")

        logger.info("Loaded %d chunks for paper %s", len(chunks), paper_id)

        # ------------------------------------------------------------------ #
        # 3. Batch-encode all chunk texts (single model call, much faster than
        #    encoding one chunk at a time)
        # ------------------------------------------------------------------ #
        texts: List[str] = [c["text"] for c in chunks]
        chunk_vectors: List[List[float]] = generate_embeddings_batch(texts)

        # ------------------------------------------------------------------ #
        # 4. Save each chunk embedding
        # ------------------------------------------------------------------ #
        for chunk, vector in zip(chunks, chunk_vectors):
            save_chunk_embedding(UUID(str(chunk["id"])), vector)

        update_job_status(job_uuid, status="running", progress=75)
        logger.info("Saved %d chunk embeddings for paper %s", len(chunks), paper_id)

        # ------------------------------------------------------------------ #
        # 5. Compute paper-level embedding as the mean of chunk vectors
        #
        #    This is the simplest acceptable approach: it produces a centroid
        #    that represents the overall semantic content of the document.
        #    The vectors are already L2-normalised individually; the mean is
        #    re-normalised below so it too is unit-length.
        # ------------------------------------------------------------------ #
        n = len(chunk_vectors)
        dim = len(chunk_vectors[0])
        mean_vector: List[float] = [
            sum(chunk_vectors[i][d] for i in range(n)) / n for d in range(dim)
        ]

        # Re-normalise the mean vector so cosine similarity stays meaningful
        magnitude = sum(v * v for v in mean_vector) ** 0.5
        if magnitude > 0:
            mean_vector = [v / magnitude for v in mean_vector]

        # ------------------------------------------------------------------ #
        # 6. Save paper embedding
        # ------------------------------------------------------------------ #
        save_paper_embedding(paper_uuid, mean_vector)
        logger.info("Saved paper embedding for paper %s", paper_id)

        # ------------------------------------------------------------------ #
        # 7. Mark embedding job completed
        # ------------------------------------------------------------------ #
        update_job_status(job_uuid, status="completed", progress=100)

        # ------------------------------------------------------------------ #
        # 8. Mark paper as ready — ingestion + embedding are done
        # ------------------------------------------------------------------ #
        set_paper_status(paper_uuid, "ready")

        # ------------------------------------------------------------------ #
        # 9. Queue a follow-up analysis job (summary, topics, clustering)
        # ------------------------------------------------------------------ #
        try:
            from app.tasks.analysis_tasks import analyze_paper_task  # noqa: PLC0415

            workspace_uuid = UUID(workspace_id)
            analysis_job = create_job(
                workspace_id=workspace_uuid,
                paper_id=paper_uuid,
                job_type="analysis",
                status="queued",
            )
            analyze_paper_task.delay(
                job_id=str(analysis_job["id"]),
                paper_id=paper_id,
                workspace_id=workspace_id,
            )
        except Exception as analysis_exc:  # noqa: BLE001
            logger.warning(
                "Failed to queue analysis job for paper %s: %s",
                paper_id,
                analysis_exc,
            )

        logger.info("Embedding task completed | paper=%s", paper_id)
        return {
            "job_id": job_id,
            "paper_id": paper_id,
            "chunks_embedded": len(chunks),
        }

    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        logger.exception(
            "Embedding task failed | job=%s paper=%s error=%s",
            job_id,
            paper_id,
            error_message,
        )
        mark_job_failed(job_uuid, error_message)
        # Embedding is considered critical — mark paper failed so the UI
        # clearly shows that search won't work for this paper.
        set_paper_status(paper_uuid, "failed")
        raise
