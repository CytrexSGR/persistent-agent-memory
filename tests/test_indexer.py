import time
import pytest
from pathlib import Path

from persistent_agent_memory.indexer import DirectoryIndexer, chunk_markdown
from persistent_agent_memory.storage.sqlite_store import SqliteStore


# --- Chunker tests ---

def test_chunk_by_headings():
    md = """# Title

Intro text.

## Section A

Content A.

## Section B

Content B.
"""
    chunks = chunk_markdown(md)
    assert len(chunks) == 3
    assert "Title" in chunks[0]
    assert "Content A" in chunks[1]
    assert "Content B" in chunks[2]


def test_chunk_no_headings():
    md = "Just a plain paragraph with no headings at all."
    chunks = chunk_markdown(md)
    assert len(chunks) == 1
    assert "plain paragraph" in chunks[0]


def test_chunk_empty():
    chunks = chunk_markdown("")
    assert chunks == []


def test_chunk_long_section_splits():
    long_text = "word " * 600
    md = f"## Big Section\n\n{long_text}"
    chunks = chunk_markdown(md, max_tokens=500)
    assert len(chunks) >= 2


# --- Indexer tests ---

@pytest.fixture
async def indexer(tmp_db, fake_embeddings):
    store = SqliteStore(tmp_db, dimensions=fake_embeddings.dimensions)
    await store.initialize()
    return DirectoryIndexer(store=store, embeddings=fake_embeddings)


@pytest.fixture
def docs_dir(tmp_path):
    (tmp_path / "readme.md").write_text("# Readme\n\nHello world.\n\n## Setup\n\nRun pip install.")
    (tmp_path / "guide.md").write_text("# Guide\n\nStep by step.")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("# Nested\n\nDeep content.")
    (tmp_path / "ignore.txt").write_text("not markdown")
    return tmp_path


async def test_index_directory(indexer, docs_dir):
    result = await indexer.index_directory(str(docs_dir), glob="**/*.md")
    assert result["files_indexed"] == 3
    assert result["chunks_created"] > 0


async def test_reindex_unchanged(indexer, docs_dir):
    r1 = await indexer.index_directory(str(docs_dir), glob="**/*.md")
    r2 = await indexer.index_directory(str(docs_dir), glob="**/*.md")
    assert r2["files_skipped"] == r1["files_indexed"]
    assert r2["files_indexed"] == 0


async def test_reindex_changed(indexer, docs_dir):
    await indexer.index_directory(str(docs_dir), glob="**/*.md")
    time.sleep(0.1)
    (docs_dir / "readme.md").write_text("# Updated\n\nNew content.")
    r2 = await indexer.index_directory(str(docs_dir), glob="**/*.md")
    assert r2["files_indexed"] >= 1


async def test_search_indexed(indexer, docs_dir):
    await indexer.index_directory(str(docs_dir), glob="**/*.md")
    results = await indexer.search(query="setup instructions", limit=5)
    assert len(results) > 0
    assert all("source_path" in r for r in results)
