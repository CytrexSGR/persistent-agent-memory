from datetime import datetime

import pytest

from persistent_agent_memory.models import Memory, IndexedChunk


def test_memory_defaults():
    m = Memory(content="test memory")
    assert m.id is not None
    assert m.category == "general"
    assert m.importance == 3
    assert m.tags == []
    assert m.source_agent == ""
    assert m.metadata == {}
    assert isinstance(m.created_at, datetime)
    assert m.embedding is None


def test_memory_with_all_fields():
    m = Memory(
        content="architecture decision",
        category="decision",
        tags=["auth", "security"],
        importance=5,
        source_agent="cypher-desktop",
        metadata={"project": "auth-rewrite"},
    )
    assert m.category == "decision"
    assert m.importance == 5
    assert "auth" in m.tags


def test_memory_invalid_category():
    with pytest.raises(Exception):
        Memory(content="test", category="invalid_category")


def test_memory_importance_bounds():
    with pytest.raises(Exception):
        Memory(content="test", importance=0)
    with pytest.raises(Exception):
        Memory(content="test", importance=6)


def test_indexed_chunk_defaults():
    c = IndexedChunk(
        source_path="/docs/readme.md",
        chunk_index=0,
        content="# Hello World",
    )
    assert c.id is not None
    assert c.embedding is None
    assert isinstance(c.indexed_at, datetime)
    assert c.file_modified_at is None
