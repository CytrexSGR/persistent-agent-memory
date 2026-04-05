import pytest

from persistent_agent_memory.models import Memory, IndexedChunk
from persistent_agent_memory.storage.sqlite_store import SqliteStore


@pytest.fixture
async def store(tmp_db):
    s = SqliteStore(tmp_db, dimensions=768)
    await s.initialize()
    return s


async def test_store_and_get_memory(store):
    mem = Memory(content="test memory", embedding=[0.1] * 768)
    stored_id = await store.store(mem)
    assert stored_id == mem.id
    retrieved = await store.get(mem.id)
    assert retrieved is not None
    assert retrieved.content == "test memory"
    assert retrieved.category == "general"


async def test_search_by_embedding(store):
    m1 = Memory(content="python programming", embedding=[0.1] * 768, tags=["code"])
    m2 = Memory(content="cooking recipes", embedding=[0.9] * 768, tags=["food"])
    await store.store(m1)
    await store.store(m2)
    results = await store.search(embedding=[0.1] * 768, limit=1, filters={})
    assert len(results) == 1
    assert results[0].content == "python programming"


async def test_search_with_category_filter(store):
    m1 = Memory(content="decision A", embedding=[0.1] * 768, category="decision")
    m2 = Memory(content="general B", embedding=[0.1] * 768, category="general")
    await store.store(m1)
    await store.store(m2)
    results = await store.search(
        embedding=[0.1] * 768, limit=10, filters={"category": "decision"}
    )
    assert all(r.category == "decision" for r in results)


async def test_delete_memory(store):
    mem = Memory(content="to be deleted", embedding=[0.1] * 768)
    await store.store(mem)
    deleted = await store.delete(mem.id)
    assert deleted is True
    assert await store.get(mem.id) is None


async def test_delete_nonexistent(store):
    deleted = await store.delete("nonexistent-id")
    assert deleted is False


async def test_list_by_category(store):
    m1 = Memory(content="rule 1", embedding=[0.1] * 768, category="rule", tags=["sec"])
    m2 = Memory(content="rule 2", embedding=[0.2] * 768, category="rule", tags=["ops"])
    m3 = Memory(content="general", embedding=[0.3] * 768, category="general")
    await store.store(m1)
    await store.store(m2)
    await store.store(m3)
    results = await store.list(category="rule", tags=[], limit=10)
    assert len(results) == 2
    assert all(r.category == "rule" for r in results)


async def test_list_by_tags(store):
    m1 = Memory(content="tagged", embedding=[0.1] * 768, tags=["alpha", "beta"])
    m2 = Memory(content="other", embedding=[0.2] * 768, tags=["gamma"])
    await store.store(m1)
    await store.store(m2)
    results = await store.list(category=None, tags=["alpha"], limit=10)
    assert len(results) == 1
    assert results[0].content == "tagged"


async def test_store_and_search_indexed_chunk(store):
    chunk = IndexedChunk(
        source_path="/docs/readme.md",
        chunk_index=0,
        content="# Hello World",
        embedding=[0.5] * 768,
    )
    await store.store_chunk(chunk)
    results = await store.search_chunks(embedding=[0.5] * 768, limit=5)
    assert len(results) == 1
    assert results[0].source_path == "/docs/readme.md"
