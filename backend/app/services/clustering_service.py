from __future__ import annotations

from typing import Dict, List, Tuple
from uuid import UUID

import numpy as np
from sklearn.cluster import KMeans

from app.db import get_db


def _parse_vector(value: str) -> List[float]:
    """Parse a pgvector string representation into a Python list of floats."""
    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    if not s:
        return []
    return [float(x) for x in s.split(",")]


def cluster_workspace_papers(workspace_id: UUID, max_clusters: int = 8) -> Dict[str, int]:
    """Cluster papers in a workspace based on their embeddings.

    Args:
        workspace_id: Workspace whose papers should be clustered.
        max_clusters: Upper bound on the number of clusters.

    Returns:
        Mapping from paper_id (string) to assigned cluster_id (int).
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, embedding
                FROM papers
                WHERE workspace_id = %s
                  AND embedding IS NOT NULL
                """,
                (str(workspace_id),),
            )
            rows: List[Tuple[str, str]] = cur.fetchall()

    if not rows:
        return {}

    paper_ids: List[str] = []
    vectors: List[List[float]] = []
    for pid, emb in rows:
        vec = _parse_vector(emb)
        if not vec:
            continue
        paper_ids.append(str(pid))
        vectors.append(vec)

    if len(paper_ids) < 2:
        # Not enough data to form clusters
        return {}

    X = np.array(vectors, dtype=float)
    n_papers = X.shape[0]
    n_clusters = max(2, min(max_clusters, n_papers))

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(X)

    id_to_cluster: Dict[str, int] = {pid: int(label) for pid, label in zip(paper_ids, labels)}

    # Persist cluster assignments
    with get_db() as conn:
        with conn.cursor() as cur:
            for pid, label in id_to_cluster.items():
                cur.execute(
                    "UPDATE papers SET cluster_id = %s WHERE id = %s",
                    (label, pid),
                )
        conn.commit()

    return id_to_cluster

