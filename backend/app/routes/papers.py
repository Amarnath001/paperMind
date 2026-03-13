from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID, uuid4

from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.db import get_db
from app.services.auth_service import require_auth
from app.services.storage_service import (
    ALLOWED_EXTENSIONS,
    allowed_file,
    save_paper_file,
    delete_paper_file,
)
from app.services.job_service import create_job
from app.services.vector_service import search_similar_papers
from app.tasks.ingestion_tasks import ingest_paper_task

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
@limiter.limit("30/hour")  # type: ignore[arg-type]
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

    # Create ingestion job and dispatch Celery task asynchronously
    job = create_job(
        workspace_id=ws_uuid,
        paper_id=paper_id,
        job_type="ingestion",
        status="queued",
        progress=0,
    )
    ingest_paper_task.delay(
        str(job["id"]),
        str(paper_id),
        str(ws_uuid),
        paper["file_path"],
    )

    return jsonify({"paper": paper, "job": {**job, "id": str(job["id"])}}), 201


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


@papers_bp.route("/<paper_id>", methods=["GET"])
def get_paper(paper_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        return jsonify({"error": "invalid paper id"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id,
                       p.workspace_id,
                       p.title,
                       p.filename,
                       p.file_path,
                       p.status,
                       p.created_at
                FROM papers p
                JOIN workspace_members m
                  ON p.workspace_id = m.workspace_id
                WHERE p.id = %s
                  AND m.user_id = %s
                """,
                (str(paper_uuid), str(user["id"])),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "paper not found"}), 404

    paper = {
        "id": row[0],
        "workspace_id": row[1],
        "title": row[2],
        "filename": row[3],
        "file_path": row[4],
        "status": row[5],
        "created_at": row[6].isoformat(),
    }
    return jsonify(paper)


@papers_bp.route("/<paper_id>", methods=["DELETE"])
def delete_paper(paper_id: str):
    """Delete a paper the user has access to, along with its stored file.

    Related rows in chunks/jobs are removed via database ON DELETE CASCADE.
    """
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        return jsonify({"error": "invalid paper id"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            # Ensure the user is a member of the workspace that owns this paper
            cur.execute(
                """
                SELECT p.file_path, p.workspace_id
                FROM   papers p
                JOIN   workspace_members m
                  ON   p.workspace_id = m.workspace_id
                WHERE  p.id = %s
                  AND  m.user_id = %s
                """,
                (str(paper_uuid), str(user["id"])),
            )
            row = cur.fetchone()

        if not row:
            return jsonify({"error": "paper not found or access denied"}), 404

        file_path = row[0]

        # Delete DB row; related chunks/jobs follow via FK cascades
        with conn.cursor() as cur:
            cur.execute("DELETE FROM papers WHERE id = %s", (str(paper_uuid),))
        conn.commit()

    # Best-effort file deletion (do not fail the API if this raises)
    try:
        if file_path:
            delete_paper_file(file_path)
    except Exception:
        pass

    return jsonify({"status": "deleted"}), 200


@papers_bp.route("/<paper_id>/similar", methods=["GET"])
def get_similar_papers(paper_id: str):
    """Find papers similar to the specified paper within the same workspace."""
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        return jsonify({"error": "invalid paper id"}), 400

    limit_val = request.args.get("limit", 5)
    try:
        limit = int(limit_val)
        if limit < 1 or limit > 50:
            limit = 5
    except ValueError:
        limit = 5

    # 1. Ensure user has access to the paper's workspace
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.workspace_id
                FROM papers p
                JOIN workspace_members m ON p.workspace_id = m.workspace_id
                WHERE p.id = %s AND m.user_id = %s
                """,
                (str(paper_uuid), str(user["id"])),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "paper not found or access denied"}), 404

    workspace_uuid = row[0]

    try:
        # 2. Search using the paper's already-stored embedding
        results = search_similar_papers(
            workspace_id=workspace_uuid,
            paper_id=paper_uuid,
            limit=limit,
        )
        return jsonify({"results": results}), 200

    except ValueError as exc:
        # E.g., paper has no embedding yet because it's still processing
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Search failed: {str(exc)}"}), 500

