from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Chunk:
    id: UUID
    paper_id: UUID
    chunk_index: int
    text: str
    token_count: int | None
    created_at: datetime
    embedding: list[float] | None = field(default=None, repr=False)

