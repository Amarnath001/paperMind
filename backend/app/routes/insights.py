from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from flask import Blueprint, jsonify

from app.db import get_db
from app.services.auth_service import require_auth
from app.services.insight_service import (
    get_workspace_clusters,
    get_workspace_insights,
)

insights_bp = Blueprint("insights", __name__)


def _user_is_member_of_workspace(conn, workspace_id: UUID, user_id: UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
            """,
            (str(workspace_id), str(user_id)),
        )
        return cur.fetchone() is not None


@insights_bp.route("/workspace/<workspace_id>", methods=["GET"])
def get_workspace_insights_route(workspace_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    with get_db() as conn:
        if not _user_is_member_of_workspace(conn, workspace_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

    insights = get_workspace_insights(workspace_uuid)

    # Normalise UUIDs and datetimes
    def _serialise_paper(p: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(p["id"]),
            "title": p["title"],
            "summary": p["summary"],
            "topics": p["topics"],
            "cluster_id": p["cluster_id"],
            "created_at": p["created_at"].isoformat(),
        }

    clusters_out: List[Dict[str, Any]] = []
    for cluster in insights.get("clusters", []):
        papers = cluster.get("papers") or []
        clusters_out.append(
            {
                "cluster_id": cluster["cluster_id"],
                "papers": [_serialise_paper(p) for p in papers],
            }
        )

    recent_out = [_serialise_paper(p) for p in insights.get("recent_papers", [])]

    topics_out = [
        {"topic": t["topic"], "count": t["count"]}
        for t in insights.get("topics", [])
    ]

    return jsonify(
        {
            "total_papers": insights.get("total_papers", 0),
            "clusters": clusters_out,
            "topics": topics_out,
            "recent_papers": recent_out,
        }
    )


@insights_bp.route("/workspace/<workspace_id>/clusters", methods=["GET"])
def get_workspace_clusters_route(workspace_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    with get_db() as conn:
        if not _user_is_member_of_workspace(conn, workspace_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

    clusters = get_workspace_clusters(workspace_uuid)

    def _serialise_paper(p: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(p["id"]),
            "title": p["title"],
            "summary": p["summary"],
            "topics": p["topics"],
            "cluster_id": p["cluster_id"],
            "created_at": p["created_at"].isoformat(),
        }

    clusters_out: List[Dict[str, Any]] = []
    for cluster in clusters:
        papers = cluster.get("papers") or []
        clusters_out.append(
            {
                "cluster_id": cluster["cluster_id"],
                "papers": [_serialise_paper(p) for p in papers],
            }
        )

    return jsonify(clusters_out)

