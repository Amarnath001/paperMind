from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class Message:
    id: UUID
    conversation_id: UUID
    role: str  # 'user' or 'assistant'
    content: str
    citations: Optional[List[Dict[str, Any]]]
    created_at: datetime

