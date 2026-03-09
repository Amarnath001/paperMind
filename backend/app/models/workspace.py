from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Workspace:
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime


@dataclass
class WorkspaceMember:
    workspace_id: UUID
    user_id: UUID
    role: str

