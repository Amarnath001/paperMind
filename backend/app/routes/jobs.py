from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.services.auth_service import require_auth

jobs_bp = Blueprint("jobs", __name__)


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


def _row_to_job(row: Any) -> Dict[str, Any]:
    return {
        "id": row[0],
        "workspace_id": row[1],
        "paper_id": row[2],
        "type": row[3],
        "status": row[4],
        "progress": row[5],
        "error": row[6],
        "created_at": row[7].isoformat(),
        "updated_at": row[8].isoformat(),
    }


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    workspace_id_param = request.args.get("workspace_id", "").strip()
    paper_id_param = request.args.get("paper_id", "").strip()

    jobs: List[Dict[str, Any]] = []

    with get_db() as conn:
        with conn.cursor() as cur:
            base_query = """
                SELECT j.id,
                       j.workspace_id,
                       j.paper_id,
                       j.type,
                       j.status,
                       j.progress,
                       j.error,
                       j.created_at,
                       j.updated_at
                FROM jobs j
                JOIN workspace_members m
                  ON j.workspace_id = m.workspace_id
                WHERE m.user_id = %s
            """
            params: List[Any] = [str(user["id"])]

            if workspace_id_param:
                try:
                    ws_uuid = UUID(workspace_id_param)
                except ValueError:
                    return jsonify({"error": "invalid workspace_id"}), 400
                base_query += " AND j.workspace_id = %s"
                params.append(str(ws_uuid))

            if paper_id_param:
                try:
                    paper_uuid = UUID(paper_id_param)
                except ValueError:
                    return jsonify({"error": "invalid paper_id"}), 400
                base_query += " AND j.paper_id = %s"
                params.append(str(paper_uuid))

            base_query += " ORDER BY j.created_at DESC"

            cur.execute(base_query, params)
            for row in cur.fetchall():
                jobs.append(_row_to_job(row))

    return jsonify(jobs)


@jobs_bp.route("/<job_id>", methods=["GET"])
def get_job(job_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        return jsonify({"error": "invalid job id"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT j.id,
                       j.workspace_id,
                       j.paper_id,
                       j.type,
                       j.status,
                       j.progress,
                       j.error,
                       j.created_at,
                       j.updated_at
                FROM jobs j
                JOIN workspace_members m
                  ON j.workspace_id = m.workspace_id
                WHERE j.id = %s
                  AND m.user_id = %s
                """,
                (str(job_uuid), str(user["id"])),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "job not found"}), 404

    return jsonify(_row_to_job(row))

