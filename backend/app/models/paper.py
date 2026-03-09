from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Paper:
    id: UUID
    workspace_id: UUID
    title: str
    filename: str
    file_path: str
    status: str
    created_at: datetime

