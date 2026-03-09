from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID, uuid4

from flask import Blueprint, current_app, jsonify, request

from app.db import get_db
from app.services.auth_service import require_auth
from app.services.storage_service import ALLOWED_EXTENSIONS, allowed_file, save_paper_file

papers_bp = Blueprint("papers", __name__)


def _user_is_member(conn, workspace_id: UUID, user_id: UUID) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
            """,
            (str(workspace_id), str(user_id)),
        )
        return cur.fetchone() is not None


@papers_bp.route("/upload", methods=["POST"])
def upload_paper():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    workspace_id = request.form.get("workspace_id", "").strip()
    title = (request.form.get("title") or "").strip()

    if not workspace_id:
        return jsonify({"error": "workspace_id is required"}), 400

    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "error": "invalid file type",
                    "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
                }
            ),
            400,
        )

    # Enforce upload size limit (in addition to MAX_CONTENT_LENGTH)
    content_length = request.content_length or 0
    if content_length > int(current_app.config["MAX_CONTENT_LENGTH"]):
        return jsonify({"error": "file too large (max 20MB)"}), 413

    try:
        ws_uuid = UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid workspace id"}), 400

    with get_db() as conn:
        if not _user_is_member(conn, ws_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

        saved_filename, relative_path = save_paper_file(file, workspace_id)
        paper_id = uuid4()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO papers (
                    id, workspace_id, title, filename, file_path, status, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, workspace_id, title, filename, file_path, status, created_at
                """,
                (
                    str(paper_id),
                    str(ws_uuid),
                    title or file.filename,
                    saved_filename,
                    relative_path,
                    "uploaded",
                ),
            )
            row = cur.fetchone()

        conn.commit()

    paper = {
        "id": row[0],
        "workspace_id": row[1],
        "title": row[2],
        "filename": row[3],
        "file_path": row[4],
        "status": row[5],
        "created_at": row[6].isoformat(),
    }
    return jsonify(paper), 201


@papers_bp.route("", methods=["GET"])
def list_papers():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    workspace_id = request.args.get("workspace_id", "").strip()
    if not workspace_id:
        return jsonify({"error": "workspace_id is required"}), 400

    try:
        ws_uuid = UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid workspace id"}), 400

    items: List[Dict[str, Any]] = []
    with get_db() as conn:
        if not _user_is_member(conn, ws_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, filename, file_path, status, created_at
                FROM papers
                WHERE workspace_id = %s
                ORDER BY created_at DESC
                """,
                (str(ws_uuid),),
            )
            for row in cur.fetchall():
                items.append(
                    {
                        "id": row[0],
                        "workspace_id": row[1],
                        "title": row[2],
                        "filename": row[3],
                        "file_path": row[4],
                        "status": row[5],
                        "created_at": row[6].isoformat(),
                    }
                )

    return jsonify(items)

