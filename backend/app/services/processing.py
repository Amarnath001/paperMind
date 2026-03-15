"""Shared processing logic for paper pipeline (sync or async via Celery).

When ASYNC_PROCESSING is false, the upload route calls these functions
inline so no separate worker is required.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from app.config import Config
from app.db import get_db
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings_batch
from app.services.job_service import (
    create_job,
    delete_chunks_for_paper,
    get_chunks_for_paper,
    insert_chunks,
    mark_job_failed,
    set_paper_status,
    update_job_status,
)
from app.services.pdf_service import extract_text_from_pdf
from app.services.vector_service import save_chunk_embedding, save_paper_embedding

logger = logging.getLogger(__name__)


def run_ingestion(
    job_id: UUID,
    paper_id: UUID,
    workspace_id: UUID,
    file_path: str,
) -> Dict[str, Any]:
    """Extract PDF text, chunk, and insert chunks. Does not queue embedding."""
    _ = workspace_id  # reserved for API consistency with Celery task
    update_job_status(job_id, status="running", progress=0)
    set_paper_status(paper_id, "processing")

    text = extract_text_from_pdf(file_path, storage_managed=True)
    if not text.strip():
        raise ValueError("No extractable text found in PDF")

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No chunks produced from extracted text")

    delete_chunks_for_paper(paper_id)
    insert_chunks(paper_id, chunks)
    update_job_status(job_id, status="completed", progress=100)
    return {"job_id": str(job_id), "paper_id": str(paper_id), "chunks": len(chunks)}


def run_embedding(
    job_id: UUID,
    paper_id: UUID,
    workspace_id: UUID,
) -> Dict[str, Any]:
    """Generate and store embeddings for all chunks and the paper. Does not queue analysis."""
    _ = workspace_id  # reserved for API consistency with Celery task
    update_job_status(job_id, status="running", progress=0)

    chunks = get_chunks_for_paper(paper_id)
    if not chunks:
        raise ValueError(f"No chunks found for paper {paper_id}. Cannot embed.")

    texts: List[str] = [c["text"] for c in chunks]
    chunk_vectors: List[List[float]] = generate_embeddings_batch(texts)

    for chunk, vector in zip(chunks, chunk_vectors):
        save_chunk_embedding(UUID(str(chunk["id"])), vector)

    update_job_status(job_id, status="running", progress=75)

    n = len(chunk_vectors)
    dim = len(chunk_vectors[0])
    mean_vector: List[float] = [
        sum(chunk_vectors[i][d] for i in range(n)) / n for d in range(dim)
    ]
    magnitude = sum(v * v for v in mean_vector) ** 0.5
    if magnitude > 0:
        mean_vector = [v / magnitude for v in mean_vector]

    save_paper_embedding(paper_id, mean_vector)
    update_job_status(job_id, status="completed", progress=100)
    set_paper_status(paper_id, "ready")
    return {"job_id": str(job_id), "paper_id": str(paper_id), "chunks_embedded": len(chunks)}


def run_analysis(
    job_id: UUID,
    paper_id: UUID,
    workspace_id: UUID,
) -> Dict[str, Any]:
    """Generate summary, topics, and optionally run clustering."""
    from app.services.summarization_service import generate_paper_summary
    from app.services.topic_service import extract_paper_topics

    update_job_status(job_id, status="running", progress=0)

    chunks = get_chunks_for_paper(paper_id)
    if not chunks:
        raise ValueError(f"No chunks found for paper {paper_id}. Cannot analyze.")

    summary = generate_paper_summary(chunks)
    topics = extract_paper_topics(chunks)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE papers
                SET summary = %s, topics = %s
                WHERE id = %s
                """,
                (summary or None, topics or None, str(paper_id)),
            )
        conn.commit()

    update_job_status(job_id, status="running", progress=70)

    if Config.ENABLE_CLUSTERING:
        try:
            from app.services.clustering_service import cluster_workspace_papers

            cluster_workspace_papers(workspace_id)
        except Exception as e:
            logger.warning("Clustering failed for workspace %s: %s", workspace_id, e)

    update_job_status(job_id, status="completed", progress=100)
    return {
        "job_id": str(job_id),
        "paper_id": str(paper_id),
        "summary_generated": bool(summary),
        "topics_count": len(topics),
    }


def run_full_pipeline_sync(
    paper_id: UUID,
    workspace_id: UUID,
    file_path: str,
) -> Dict[str, Any]:
    """Run ingest -> embed -> analysis synchronously. Creates and updates jobs.
    Returns dict with 'job' (ingestion job for API response) and job ids.
    """
    ingestion_job = create_job(
        workspace_id=workspace_id,
        paper_id=paper_id,
        job_type="ingestion",
        status="queued",
        progress=0,
    )
    ingestion_job_id = UUID(str(ingestion_job["id"]))

    try:
        run_ingestion(ingestion_job_id, paper_id, workspace_id, file_path)
    except Exception as e:
        mark_job_failed(ingestion_job_id, str(e))
        set_paper_status(paper_id, "failed")
        raise

    embedding_job = create_job(
        workspace_id=workspace_id,
        paper_id=paper_id,
        job_type="embedding",
        status="queued",
        progress=0,
    )
    embedding_job_id = UUID(str(embedding_job["id"]))

    try:
        run_embedding(embedding_job_id, paper_id, workspace_id)
    except Exception as e:
        mark_job_failed(embedding_job_id, str(e))
        set_paper_status(paper_id, "failed")
        raise

    analysis_job = create_job(
        workspace_id=workspace_id,
        paper_id=paper_id,
        job_type="analysis",
        status="queued",
        progress=0,
    )
    analysis_job_id = UUID(str(analysis_job["id"]))

    try:
        run_analysis(analysis_job_id, paper_id, workspace_id)
    except Exception as e:
        mark_job_failed(analysis_job_id, str(e))
        # Paper stays ready; analysis is non-critical

    return {
        "job": ingestion_job,
        "ingestion_job_id": str(ingestion_job_id),
        "embedding_job_id": str(embedding_job_id),
        "analysis_job_id": str(analysis_job_id),
    }
