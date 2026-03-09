from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID, uuid4

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.services.auth_service import require_auth

workspaces_bp = Blueprint("workspaces", __name__)


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


@workspaces_bp.route("", methods=["POST"])
def create_workspace():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    workspace_id = uuid4()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspaces (id, name, owner_id, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id, name, owner_id, created_at
                """,
                (str(workspace_id), name, str(user["id"])),
            )
            ws_row = cur.fetchone()

            cur.execute(
                """
                INSERT INTO workspace_members (workspace_id, user_id, role)
                VALUES (%s, %s, %s)
                """,
                (str(workspace_id), str(user["id"]), "owner"),
            )

        conn.commit()

    workspace = {
        "id": ws_row[0],
        "name": ws_row[1],
        "owner_id": ws_row[2],
        "created_at": ws_row[3].isoformat(),
    }
    return jsonify(workspace), 201


@workspaces_bp.route("", methods=["GET"])
def list_workspaces():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    items: List[Dict[str, Any]] = []
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT w.id, w.name, w.owner_id, w.created_at, m.role
                FROM workspaces w
                JOIN workspace_members m
                  ON w.id = m.workspace_id
                WHERE m.user_id = %s
                ORDER BY w.created_at DESC
                """,
                (str(user["id"]),),
            )
            for row in cur.fetchall():
                items.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "owner_id": row[2],
                        "created_at": row[3].isoformat(),
                        "role": row[4],
                    }
                )

    return jsonify(items)


@workspaces_bp.route("/<workspace_id>", methods=["GET"])
def get_workspace(workspace_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        ws_uuid = UUID(workspace_id)
    except ValueError:
        return jsonify({"error": "invalid workspace id"}), 400

    with get_db() as conn:
        if not _user_is_member(conn, ws_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, owner_id, created_at
                FROM workspaces
                WHERE id = %s
                """,
                (str(ws_uuid),),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "workspace not found"}), 404

    workspace = {
        "id": row[0],
        "name": row[1],
        "owner_id": row[2],
        "created_at": row[3].isoformat(),
    }
    return jsonify(workspace)

