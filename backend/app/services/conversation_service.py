from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.db import get_db


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


def create_conversation(workspace_id: UUID, created_by: UUID, title: Optional[str] = None) -> Dict[str, Any]:
    conversation_id = uuid4()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    id, workspace_id, title, created_by, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING id, workspace_id, title, created_by, created_at, updated_at
                """,
                (str(conversation_id), str(workspace_id), title, str(created_by)),
            )
            row = cur.fetchone()
        conn.commit()

    return _row_to_conversation(row)


def list_conversations(workspace_id: UUID, user_id: UUID) -> List[Dict[str, Any]]:
    """List conversations for a workspace, ensuring the user is a member."""
    with get_db() as conn:
        if not _user_is_member_of_workspace(conn, workspace_id, user_id):
            return []

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, created_by, created_at, updated_at
                FROM conversations
                WHERE workspace_id = %s
                ORDER BY updated_at DESC
                """,
                (str(workspace_id),),
            )
            rows = cur.fetchall()

    return [_row_to_conversation(row) for row in rows]


def get_conversation(conversation_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
    """Return a conversation if the user is allowed to access it."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, workspace_id, title, created_by, created_at, updated_at
                FROM conversations
                WHERE id = %s
                """,
                (str(conversation_id),),
            )
            row = cur.fetchone()

        if not row:
            return None

        workspace_id = row[1]
        if not _user_is_member_of_workspace(conn, workspace_id, user_id):
            return None

    return _row_to_conversation(row)


def save_message(
    conversation_id: UUID,
    role: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Persist a message and bump the parent conversation's updated_at."""
    message_id = uuid4()
    citations_json = json.dumps(citations) if citations is not None else None

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (
                    id, conversation_id, role, content, citations, created_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
                RETURNING id, conversation_id, role, content, citations, created_at
                """,
                (str(message_id), str(conversation_id), role, content, citations_json),
            )
            row = cur.fetchone()

            # Update conversation's updated_at
            cur.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (str(conversation_id),),
            )

        conn.commit()

    return _row_to_message(row)


def list_messages(conversation_id: UUID, user_id: UUID) -> List[Dict[str, Any]]:
    """Return all messages for a conversation, enforcing workspace membership."""
    with get_db() as conn:
        # First ensure the user has access by looking up the workspace_id
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT workspace_id
                FROM conversations
                WHERE id = %s
                """,
                (str(conversation_id),),
            )
            row = cur.fetchone()

        if not row:
            return []

        workspace_id = row[0]
        if not _user_is_member_of_workspace(conn, workspace_id, user_id):
            return []

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, conversation_id, role, content, citations, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                """,
                (str(conversation_id),),
            )
            rows = cur.fetchall()

    return [_row_to_message(r) for r in rows]


def _row_to_conversation(row: Any) -> Dict[str, Any]:
    return {
        "id": row[0],
        "workspace_id": row[1],
        "title": row[2],
        "created_by": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }


def _row_to_message(row: Any) -> Dict[str, Any]:
    citations = row[4]
    # psycopg2 will decode jsonb to a Python object automatically when possible
    return {
        "id": row[0],
        "conversation_id": row[1],
        "role": row[2],
        "content": row[3],
        "citations": citations,
        "created_at": row[5],
    }

