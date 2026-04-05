from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


MemoryCategory = Literal["general", "decision", "rule", "context", "handoff", "project"]


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: list[float] | None = None
    category: MemoryCategory = "general"
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_agent: str = ""
    metadata: dict = Field(default_factory=dict)


class IndexedChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    chunk_index: int
    content: str
    embedding: list[float] | None = None
    indexed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_modified_at: datetime | None = None
