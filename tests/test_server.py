import json
import pytest

from persistent_agent_memory.server import create_app
from persistent_agent_memory.config import Settings
from persistent_agent_memory.storage.sqlite_store import SqliteStore
from tests.conftest import FakeEmbeddingProvider


@pytest.fixture
async def app(tmp_db):
    settings = Settings(
        SQLITE_PATH=tmp_db,
        EMBEDDING_API_URL="http://unused",
        EMBEDDING_MODEL="unused",
        EMBEDDING_DIMENSIONS=768,
    )
    embeddings = FakeEmbeddingProvider(dimensions=768)
    store = SqliteStore(tmp_db, dimensions=768)
    await store.initialize()
    return create_app(settings=settings, store=store, embeddings=embeddings)


def _parse(result):
    """Extract text from call_tool result (tuple of (content_list, meta))."""
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


async def test_remember_tool(app):
    result = await app.call_tool("remember", {
        "content": "test memory", "category": "general", "tags": ["test"], "importance": 3,
    })
    data = _parse(result)
    assert "id" in data
    assert data["content"] == "test memory"


async def test_recall_tool(app):
    await app.call_tool("remember", {"content": "python programming", "category": "general"})
    result = await app.call_tool("recall", {"query": "programming", "limit": 5})
    data = _parse(result)
    assert len(data) > 0


async def test_forget_tool(app):
    r = await app.call_tool("remember", {"content": "temporary"})
    mem_id = _parse(r)["id"]
    result = await app.call_tool("forget", {"memory_id": mem_id})
    data = _parse(result)
    assert data["deleted"] is True


async def test_remember_decision_tool(app):
    result = await app.call_tool("remember_decision", {
        "decision": "Use SQLite", "context": "Single user setup", "rationale": "Zero dependency",
    })
    data = _parse(result)
    assert data["category"] == "decision"


async def test_remember_rule_tool(app):
    result = await app.call_tool("remember_rule", {
        "rule": "Always test first", "reason": "TDD prevents regressions",
    })
    data = _parse(result)
    assert data["category"] == "rule"


async def test_get_bootstrap_context_tool(app):
    await app.call_tool("remember", {"content": "a decision", "category": "decision"})
    result = await app.call_tool("get_bootstrap_context", {})
    data = _parse(result)
    assert "decisions" in data
    assert "rules" in data
    assert "handoffs" in data


async def test_get_session_summary_tool(app):
    await app.call_tool("remember", {"content": "session note"})
    result = await app.call_tool("get_session_summary", {"limit": 5})
    data = _parse(result)
    assert len(data) > 0


async def test_search_knowledge_tool(app):
    await app.call_tool("remember", {"content": "deep fact", "importance": 5})
    result = await app.call_tool("search_knowledge", {"query": "fact", "limit": 5})
    data = _parse(result)
    assert len(data) > 0


async def test_get_context_tool(app):
    await app.call_tool("remember", {"content": "topic info", "tags": ["topic"]})
    result = await app.call_tool("get_context", {"topic": "topic info"})
    data = _parse(result)
    assert data["topic"] == "topic info"
    assert "memories" in data
