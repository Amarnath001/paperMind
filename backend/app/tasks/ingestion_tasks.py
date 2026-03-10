from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from celery import Task

from app.celery_app import celery
from app.services.chunking_service import chunk_text
from app.services.job_service import (
    create_job,
    delete_chunks_for_paper,
    has_pending_embedding_job,
    insert_chunks,
    mark_job_failed,
    set_paper_status,
    update_job_status,
)
from app.services.pdf_service import extract_text_from_pdf


@celery.task(bind=True, name="app.tasks.ingest_paper")
def ingest_paper_task(
    self: Task,
    job_id: str,
    paper_id: str,
    workspace_id: str,  # kept for future use / validation
    file_path: str,
) -> Dict[str, Any]:
    """Background task to ingest a paper: extract, chunk, and store text."""
    job_uuid = UUID(job_id)
    paper_uuid = UUID(paper_id)

    try:
        # Mark job as running and paper as processing
        update_job_status(job_uuid, status="running", progress=0)
        set_paper_status(paper_uuid, "processing")

        # Extract text
        text = extract_text_from_pdf(file_path)
        if not text.strip():
            raise ValueError("No extractable text found in PDF")

        # Chunk text
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No chunks produced from extracted text")

        # Idempotency: clear existing chunks, then insert new ones
        delete_chunks_for_paper(paper_uuid)
        insert_chunks(paper_uuid, chunks)

        # Queue the follow-up embedding job (idempotent: skip if one is active)
        workspace_uuid = UUID(workspace_id)
        if not has_pending_embedding_job(paper_uuid):
            embedding_job = create_job(
                workspace_id=workspace_uuid,
                paper_id=paper_uuid,
                job_type="embedding",
                status="queued",
            )
            from app.tasks.embedding_tasks import embed_paper_task  # noqa: PLC0415
            embed_paper_task.delay(
                job_id=str(embedding_job["id"]),
                paper_id=paper_id,
                workspace_id=workspace_id,
            )

        # Mark ingestion as completed (embedding runs independently)
        set_paper_status(paper_uuid, "processing")  # still processing — embedding pending
        update_job_status(job_uuid, status="completed", progress=100)

        return {"job_id": job_id, "paper_id": paper_id, "chunks": len(chunks)}

    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        mark_job_failed(job_uuid, error_message)
        set_paper_status(paper_uuid, "failed")
        # Re-raise to allow Celery to record failure, but we've already
        # updated our own job tracking.
        raise

