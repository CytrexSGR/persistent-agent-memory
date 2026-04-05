import os
import pytest

from persistent_agent_memory.models import Memory, IndexedChunk

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set — skipping Postgres tests",
)


@pytest.fixture
async def store():
    from persistent_agent_memory.storage.postgres_store import PostgresStore

    s = PostgresStore(os.environ["TEST_DATABASE_URL"], dimensions=768)
    await s.initialize()
    yield s
    await s.cleanup()


async def test_store_and_get(store):
    mem = Memory(content="postgres test", embedding=[0.1] * 768)
    await store.store(mem)
    retrieved = await store.get(mem.id)
    assert retrieved is not None
    assert retrieved.content == "postgres test"


async def test_search(store):
    m1 = Memory(content="python", embedding=[0.1] * 768)
    m2 = Memory(content="cooking", embedding=[0.9] * 768)
    await store.store(m1)
    await store.store(m2)
    results = await store.search(embedding=[0.1] * 768, limit=1, filters={})
    assert len(results) == 1
    assert results[0].content == "python"


async def test_delete(store):
    mem = Memory(content="delete me", embedding=[0.1] * 768)
    await store.store(mem)
    assert await store.delete(mem.id) is True
    assert await store.get(mem.id) is None


async def test_list_by_category(store):
    m1 = Memory(content="rule", embedding=[0.1] * 768, category="rule")
    m2 = Memory(content="general", embedding=[0.2] * 768, category="general")
    await store.store(m1)
    await store.store(m2)
    results = await store.list(category="rule", tags=[], limit=10)
    assert all(r.category == "rule" for r in results)


async def test_chunks(store):
    chunk = IndexedChunk(
        source_path="/test.md", chunk_index=0,
        content="test chunk", embedding=[0.5] * 768,
    )
    await store.store_chunk(chunk)
    results = await store.search_chunks(embedding=[0.5] * 768, limit=5)
    assert len(results) >= 1
