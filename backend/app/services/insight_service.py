from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from app.db import get_db


def get_workspace_insights(workspace_id: UUID) -> Dict[str, Any]:
    """Return high-level insights for a workspace."""
    insights: Dict[str, Any] = {}

    with get_db() as conn:
        with conn.cursor() as cur:
            # Total papers
            cur.execute(
                "SELECT COUNT(*) FROM papers WHERE workspace_id = %s",
                (str(workspace_id),),
            )
            total_papers = cur.fetchone()[0]
            insights["total_papers"] = int(total_papers)

            # Clusters with papers
            cur.execute(
                """
                SELECT
                    cluster_id,
                    json_agg(
                        json_build_object(
                            'id', p.id,
                            'title', p.title,
                            'summary', p.summary,
                            'topics', p.topics,
                            'created_at', p.created_at
                        )
                        ORDER BY p.created_at DESC
                    ) AS papers
                FROM papers p
                WHERE p.workspace_id = %s
                  AND p.cluster_id IS NOT NULL
                GROUP BY cluster_id
                ORDER BY cluster_id
                """,
                (str(workspace_id),),
            )
            cluster_rows = cur.fetchall()
            clusters: List[Dict[str, Any]] = []
            for cluster_id, papers_json in cluster_rows:
                clusters.append(
                    {
                        "cluster_id": int(cluster_id),
                        "papers": papers_json or [],
                    }
                )
            insights["clusters"] = clusters

            # Topics (aggregated)
            cur.execute(
                """
                SELECT topic, COUNT(*) AS count
                FROM (
                    SELECT unnest(topics) AS topic
                    FROM papers
                    WHERE workspace_id = %s
                      AND topics IS NOT NULL
                ) t
                GROUP BY topic
                ORDER BY count DESC, topic ASC
                LIMIT 20
                """,
                (str(workspace_id),),
            )
            topic_rows = cur.fetchall()
            insights["topics"] = [
                {"topic": row[0], "count": int(row[1])} for row in topic_rows
            ]

            # Recent papers
            cur.execute(
                """
                SELECT id, title, summary, topics, cluster_id, created_at
                FROM papers
                WHERE workspace_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (str(workspace_id),),
            )
            recent_rows = cur.fetchall()
            recent_papers: List[Dict[str, Any]] = []
            for row in recent_rows:
                recent_papers.append(
                    {
                        "id": row[0],
                        "title": row[1],
                        "summary": row[2],
                        "topics": row[3],
                        "cluster_id": row[4],
                        "created_at": row[5],
                    }
                )
            insights["recent_papers"] = recent_papers

    return insights


def get_workspace_clusters(workspace_id: UUID) -> List[Dict[str, Any]]:
    """Return cluster groups for a workspace."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    cluster_id,
                    json_agg(
                        json_build_object(
                            'id', p.id,
                            'title', p.title,
                            'summary', p.summary,
                            'topics', p.topics,
                            'created_at', p.created_at
                        )
                        ORDER BY p.created_at DESC
                    ) AS papers
                FROM papers p
                WHERE p.workspace_id = %s
                  AND p.cluster_id IS NOT NULL
                GROUP BY cluster_id
                ORDER BY cluster_id
                """,
                (str(workspace_id),),
            )
            rows = cur.fetchall()

    clusters: List[Dict[str, Any]] = []
    for cluster_id, papers_json in rows:
        clusters.append(
            {
                "cluster_id": int(cluster_id),
                "papers": papers_json or [],
            }
        )
    return clusters

