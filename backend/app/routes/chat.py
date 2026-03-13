from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from flask import Blueprint, jsonify, request

from app import limiter
from app.db import get_db
from app.services.auth_service import require_auth
from app.services.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    save_message,
)
from app.services.llm_service import LLMService
from app.services.retrieval_service import retrieve_context_for_question

chat_bp = Blueprint("chat", __name__)


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


def _validate_paper_access(conn, workspace_id: UUID, paper_id: UUID) -> bool:
    """Return True if the paper exists and belongs to the workspace."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM papers
            WHERE id = %s AND workspace_id = %s
            """,
            (str(paper_id), str(workspace_id)),
        )
        return cur.fetchone() is not None


@chat_bp.route("/conversations", methods=["POST"])
def create_conversation_route():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    data = request.get_json() or {}
    workspace_id_str = (data.get("workspace_id") or "").strip()
    title = (data.get("title") or "").strip() or None

    if not workspace_id_str:
        return jsonify({"error": "workspace_id is required"}), 400

    try:
        workspace_uuid = UUID(workspace_id_str)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    with get_db() as conn:
        if not _user_is_member_of_workspace(conn, workspace_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

    conv = create_conversation(workspace_uuid, user["id"], title=title)
    # Normalise UUID/string fields for JSON
    conv_out = {
        "id": str(conv["id"]),
        "workspace_id": str(conv["workspace_id"]),
        "title": conv["title"],
        "created_by": str(conv["created_by"]),
        "created_at": conv["created_at"].isoformat(),
        "updated_at": conv["updated_at"].isoformat(),
    }
    return jsonify(conv_out), 201


@chat_bp.route("/conversations", methods=["GET"])
def list_conversations_route():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    workspace_id_str = request.args.get("workspace_id", "").strip()
    if not workspace_id_str:
        return jsonify({"error": "workspace_id is required"}), 400

    try:
        workspace_uuid = UUID(workspace_id_str)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    conversations = list_conversations(workspace_uuid, user["id"])
    items: List[Dict[str, Any]] = []
    for conv in conversations:
        items.append(
            {
                "id": str(conv["id"]),
                "workspace_id": str(conv["workspace_id"]),
                "title": conv["title"],
                "created_by": str(conv["created_by"]),
                "created_at": conv["created_at"].isoformat(),
                "updated_at": conv["updated_at"].isoformat(),
            }
        )
    return jsonify(items)


@chat_bp.route("/conversations/<conversation_id>/messages", methods=["GET"])
def list_messages_route(conversation_id: str):
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError:
        return jsonify({"error": "invalid conversation id"}), 400

    messages = list_messages(conversation_uuid, user["id"])
    if not messages:
        # Could be either "no messages" or "no access"; both look the same to the client.
        return jsonify([])

    out: List[Dict[str, Any]] = []
    for msg in messages:
        out.append(
            {
                "id": str(msg["id"]),
                "conversation_id": str(msg["conversation_id"]),
                "role": msg["role"],
                "content": msg["content"],
                "citations": msg["citations"],
                "created_at": msg["created_at"].isoformat(),
            }
        )
    return jsonify(out)


@chat_bp.route("/ask", methods=["POST"])
@limiter.limit("60/hour")  # type: ignore[arg-type]
def ask_route():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    data = request.get_json() or {}
    workspace_id_str = (data.get("workspace_id") or "").strip()
    conversation_id_str = (data.get("conversation_id") or "").strip()
    question = (data.get("question") or "").strip()
    limit_val = data.get("limit", 8)
    paper_id_str = (data.get("paper_id") or "").strip() or None

    if not workspace_id_str:
        return jsonify({"error": "workspace_id is required"}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        workspace_uuid = UUID(workspace_id_str)
    except ValueError:
        return jsonify({"error": "invalid workspace_id"}), 400

    try:
        limit = int(limit_val)
        if limit < 1 or limit > 20:
            limit = 8
    except (TypeError, ValueError):
        limit = 8

    paper_uuid: Optional[UUID] = None
    if paper_id_str:
        try:
            paper_uuid = UUID(paper_id_str)
        except ValueError:
            return jsonify({"error": "invalid paper_id"}), 400

    # Validate workspace membership (and, optionally, paper access)
    with get_db() as conn:
        if not _user_is_member_of_workspace(conn, workspace_uuid, user["id"]):
            return jsonify({"error": "not a member of this workspace"}), 403

        if paper_uuid is not None:
            if not _validate_paper_access(conn, workspace_uuid, paper_uuid):
                # Optional defensive logging, without leaking details to the client
                # (A real deployment might log via a structured logger instead.)
                print("Invalid paper_id access attempt")  # noqa: T201
                return jsonify({"error": "Paper not found or access denied"}), 404

    # Resolve conversation or create a new one if not provided
    if conversation_id_str:
        try:
            conversation_uuid = UUID(conversation_id_str)
        except ValueError:
            return jsonify({"error": "invalid conversation_id"}), 400

        conv = get_conversation(conversation_uuid, user["id"])
        if not conv:
            return jsonify({"error": "conversation not found or access denied"}), 404
    else:
        # Auto-create a conversation with a generic title
        conv = create_conversation(workspace_uuid, user["id"], title="New conversation")
        conversation_uuid = conv["id"]

    # 3. Save user question as a message
    user_msg = save_message(conversation_uuid, role="user", content=question)

    # 4. Retrieve relevant chunks
    retrieved_chunks = retrieve_context_for_question(
        workspace_id=workspace_uuid,
        question=question,
        limit=limit,
        paper_id=paper_uuid,
    )

    llm = LLMService()

    # 5. Generate answer with citations (or a fallback if no chunks)
    rag_output = llm.generate_answer_with_citations(question, retrieved_chunks)
    answer_text = rag_output["answer"]
    citations = rag_output.get("citations", [])

    # 6. Save assistant answer as a message
    assistant_msg = save_message(
        conversation_uuid,
        role="assistant",
        content=answer_text,
        citations=citations,
    )

    # Normalise messages for response
    def _serialise_message(msg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(msg["id"]),
            "conversation_id": str(msg["conversation_id"]),
            "role": msg["role"],
            "content": msg["content"],
            "citations": msg["citations"],
            "created_at": msg["created_at"].isoformat(),
        }

    return jsonify(
        {
            "answer": answer_text,
            "citations": citations,
            "retrieved_chunks": retrieved_chunks,
            "conversation_id": str(conversation_uuid),
            "messages": [
                _serialise_message(user_msg),
                _serialise_message(assistant_msg),
            ],
        }
    )

