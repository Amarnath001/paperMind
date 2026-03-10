from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Conversation:
    id: UUID
    workspace_id: UUID
    title: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

