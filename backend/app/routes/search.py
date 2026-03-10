from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.services.auth_service import require_auth
from app.services.embedding_service import generate_embedding
from app.services.vector_service import search_similar_chunks

search_bp = Blueprint("search", __name__)


def _user_is_member(conn: Any, workspace_id: UUID, user_id: UUID) -> bool:
    """Check if the given user is a member of the workspace.
    Copied/adapted from the workspace/paper routes to keep auth checks local.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
            """,
            (str(workspace_id), str(user_id)),
        )
        return cur.fetchone() is not None


@search_bp.route("", methods=["POST"])
def search():
    """Semantic search over chunk embeddings within a workspace.

    Request JSON:
    {
        "workspace_id": "uuid-string",
        "query": "string",
        "limit": 10 (optional)
    }
    """
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    workspace_id_str = data.get("workspace_id", "").strip()
    query_text = data.get("query", "").strip()
    limit_val = data.get("limit", 10)

    if not workspace_id_str:
        return jsonify({"error": "workspace_id is required"}), 400
    if not query_text:
        return jsonify({"error": "query is required"}), 400

    try:
        ws_uuid = UUID(workspace_id_str)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    try:
        limit = int(limit_val)
        if limit < 1 or limit > 100:
            limit = 10
    except ValueError:
        limit = 10

    # 1. Validate workspace membership
    with get_db() as conn:
        if not _user_is_member(conn, ws_uuid, UUID(user["id"])):
            return jsonify({"error": "not a member of this workspace"}), 403

    try:
        # 2. Generate local embedding using Sentence Transformers
        query_embedding = generate_embedding(query_text)

        # 3. Search chunk embeddings within that workspace
        results = search_similar_chunks(
            workspace_id=ws_uuid,
            query_embedding=query_embedding,
            limit=limit,
        )

        return jsonify({"results": results}), 200

    except Exception as exc:
        return jsonify({"error": f"Search failed: {str(exc)}"}), 500
