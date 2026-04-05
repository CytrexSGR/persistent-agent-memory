from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from persistent_agent_memory.models import IndexedChunk
from persistent_agent_memory.embeddings.base import EmbeddingProvider
from persistent_agent_memory.storage.base import StorageBackend


def chunk_markdown(text: str, max_tokens: int = 500) -> list[str]:
    """Split markdown by headings, then by token windows for long sections."""
    if not text.strip():
        return []

    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks = []
    for section in sections:
        words = section.split()
        if len(words) <= max_tokens:
            chunks.append(section)
        else:
            step = max_tokens - 50  # 50 word overlap
            for i in range(0, len(words), step):
                window = " ".join(words[i : i + max_tokens])
                if window.strip():
                    chunks.append(window)
    return chunks


class DirectoryIndexer:
    def __init__(self, store: StorageBackend, embeddings: EmbeddingProvider):
        self._store = store
        self._embeddings = embeddings

    async def index_directory(self, path: str, glob: str = "**/*.md") -> dict:
        root = Path(path)
        files = sorted(root.glob(glob))

        files_indexed = 0
        files_skipped = 0
        chunks_created = 0

        for file_path in files:
            if not file_path.is_file():
                continue

            file_mtime = datetime.fromtimestamp(
                file_path.stat().st_mtime, tz=timezone.utc
            )
            str_path = str(file_path)

            existing = await self._store.get_chunks_by_path(str_path)
            if existing and existing[0].file_modified_at:
                existing_mtime = existing[0].file_modified_at
                if isinstance(existing_mtime, str):
                    existing_mtime = datetime.fromisoformat(existing_mtime)
                if existing_mtime and existing_mtime >= file_mtime:
                    files_skipped += 1
                    continue

            await self._store.delete_chunks_by_path(str_path)

            content = file_path.read_text(encoding="utf-8", errors="replace")
            chunks = chunk_markdown(content)
            if not chunks:
                continue

            embeddings = await self._embeddings.embed_batch(chunks)
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = IndexedChunk(
                    source_path=str_path,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=embedding,
                    file_modified_at=file_mtime,
                )
                await self._store.store_chunk(chunk)
                chunks_created += 1

            files_indexed += 1

        return {
            "files_indexed": files_indexed,
            "files_skipped": files_skipped,
            "chunks_created": chunks_created,
            "total_files": len(files),
        }

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        embedding = await self._embeddings.embed(query)
        chunks = await self._store.search_chunks(embedding=embedding, limit=limit)
        return [
            {
                "source_path": c.source_path,
                "chunk_index": c.chunk_index,
                "content": c.content,
            }
            for c in chunks
        ]
