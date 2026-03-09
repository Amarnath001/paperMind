from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Job:
    id: UUID
    workspace_id: UUID
    paper_id: Optional[UUID]
    type: str
    status: str
    progress: int
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

