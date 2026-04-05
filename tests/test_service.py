import pytest

from persistent_agent_memory.service import MemoryService
from persistent_agent_memory.storage.sqlite_store import SqliteStore


@pytest.fixture
async def service(tmp_db, fake_embeddings):
    store = SqliteStore(tmp_db, dimensions=fake_embeddings.dimensions)
    await store.initialize()
    return MemoryService(store=store, embeddings=fake_embeddings)


async def test_remember(service):
    result = await service.remember(
        content="important fact", category="general", tags=["test"], importance=4,
    )
    assert "id" in result
    assert result["content"] == "important fact"


async def test_recall(service):
    await service.remember(content="python is great", category="general", tags=["code"])
    await service.remember(content="cooking is fun", category="general", tags=["food"])
    results = await service.recall(query="programming languages", limit=5)
    assert len(results) > 0
    assert all("id" in r for r in results)


async def test_recall_with_category_filter(service):
    await service.remember(content="use TDD", category="rule", tags=["dev"])
    await service.remember(content="general note", category="general", tags=[])
    results = await service.recall(query="testing", limit=10, category="rule")
    assert all(r["category"] == "rule" for r in results)


async def test_forget(service):
    result = await service.remember(content="temporary", category="general")
    deleted = await service.forget(result["id"])
    assert deleted is True


async def test_forget_nonexistent(service):
    deleted = await service.forget("nonexistent")
    assert deleted is False


async def test_remember_decision(service):
    result = await service.remember_decision(
        decision="Use SQLite as default backend",
        context="Need zero-dependency setup for single users",
        rationale="SQLite is serverless and supports vector search via sqlite-vec",
    )
    assert result["category"] == "decision"
    assert "SQLite" in result["content"]


async def test_remember_rule(service):
    result = await service.remember_rule(
        rule="Always validate embeddings dimension before storing",
        reason="Mismatched dimensions cause silent search failures",
    )
    assert result["category"] == "rule"


async def test_get_session_summary(service):
    await service.remember(content="did thing A", category="context")
    await service.remember(content="did thing B", category="context")
    summary = await service.get_session_summary(limit=5)
    assert len(summary) >= 2


async def test_get_bootstrap_context(service):
    await service.remember(content="arch decision", category="decision", importance=5)
    await service.remember(content="important rule", category="rule", importance=5)
    await service.remember(content="ongoing handoff", category="handoff", tags=["in_progress"])
    ctx = await service.get_bootstrap_context()
    assert "decisions" in ctx
    assert "rules" in ctx
    assert "handoffs" in ctx


async def test_bootstrap_context_caching(service):
    await service.remember(content="decision A", category="decision")
    ctx1 = await service.get_bootstrap_context()
    ctx2 = await service.get_bootstrap_context()
    assert ctx1 is ctx2


async def test_search_knowledge(service):
    await service.remember(content="deep knowledge about X", category="project", importance=5)
    results = await service.search_knowledge(query="knowledge X", limit=5, threshold=0.0)
    assert len(results) > 0


async def test_get_context(service):
    await service.remember(content="topic info about databases", tags=["topic"])
    result = await service.get_context(topic="databases")
    assert result["topic"] == "databases"
    assert "memories" in result
