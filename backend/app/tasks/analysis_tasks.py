from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from app.celery_app import celery
from app.db import get_db
from app.services.clustering_service import cluster_workspace_papers
from app.services.job_service import (
    get_chunks_for_paper,
    mark_job_failed,
    update_job_status,
)
from app.services.summarization_service import generate_paper_summary
from app.services.topic_service import extract_paper_topics

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="app.tasks.analyze_paper")
def analyze_paper_task(
    self: Any,
    job_id: str,
    paper_id: str,
    workspace_id: str,
) -> Dict[str, Any]:
    """Run post-embedding analysis for a paper (summary, topics, clustering)."""
    job_uuid = UUID(job_id)
    paper_uuid = UUID(paper_id)
    workspace_uuid = UUID(workspace_id)

    logger.info(
        "Starting analysis task | job=%s paper=%s workspace=%s",
        job_id,
        paper_id,
        workspace_id,
    )

    try:
        update_job_status(job_uuid, status="running", progress=0)

        # 1. Load chunks for the paper
        chunks = get_chunks_for_paper(paper_uuid)
        if not chunks:
            raise ValueError(f"No chunks found for paper {paper_id}. Cannot analyze.")

        # 2. Generate summary
        summary = generate_paper_summary(chunks)

        # 3. Extract topics
        topics = extract_paper_topics(chunks)

        # 4. Persist summary and topics to the papers table
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE papers
                    SET summary = %s,
                        topics  = %s
                    WHERE id   = %s
                    """,
                    (summary or None, topics or None, str(paper_uuid)),
                )
            conn.commit()

        update_job_status(job_uuid, status="running", progress=70)

        # 5. Optionally run workspace-level clustering
        try:
            cluster_workspace_papers(workspace_uuid)
        except Exception as cluster_exc:  # noqa: BLE001
            logger.warning(
                "Clustering failed for workspace %s: %s",
                workspace_id,
                cluster_exc,
            )

        update_job_status(job_uuid, status="completed", progress=100)

        logger.info("Analysis task completed | paper=%s", paper_id)
        return {
            "job_id": job_id,
            "paper_id": paper_id,
            "summary_generated": bool(summary),
            "topics_count": len(topics),
        }

    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        logger.exception(
            "Analysis task failed | job=%s paper=%s error=%s",
            job_id,
            paper_id,
            error_message,
        )
        mark_job_failed(job_uuid, error_message)
        # Do not change paper.status; analysis is non-critical.
        raise

