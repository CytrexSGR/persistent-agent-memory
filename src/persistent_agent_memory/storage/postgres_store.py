from __future__ import annotations

import json

from persistent_agent_memory.models import Memory, IndexedChunk
from .base import StorageBackend


class PostgresStore(StorageBackend):
    def __init__(self, database_url: str, dimensions: int):
        self._database_url = database_url
        self._dimensions = dimensions
        self._pool = None

    async def initialize(self) -> None:
        import asyncpg
        from pgvector.asyncpg import register_vector

        self._pool = await asyncpg.create_pool(self._database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self._dimensions}),
                    category TEXT NOT NULL DEFAULT 'general',
                    tags JSONB NOT NULL DEFAULT '[]',
                    importance INTEGER NOT NULL DEFAULT 3,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    source_agent TEXT NOT NULL DEFAULT '',
                    metadata JSONB NOT NULL DEFAULT '{{}}'
                )
            """)
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS indexed_chunks (
                    id TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({self._dimensions}),
                    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    file_modified_at TIMESTAMPTZ
                )
            """)

    async def cleanup(self) -> None:
        """Drop test tables. Only for testing."""
        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute("DROP TABLE IF EXISTS memories CASCADE")
                await conn.execute("DROP TABLE IF EXISTS indexed_chunks CASCADE")
            await self._pool.close()

    async def store(self, memory: Memory) -> str:
        from pgvector.asyncpg import register_vector

        async with self._pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute(
                """INSERT INTO memories (id, content, embedding, category, tags, importance,
                   created_at, updated_at, source_agent, metadata)
                   VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10::jsonb)
                   ON CONFLICT (id) DO UPDATE SET
                   content=EXCLUDED.content, embedding=EXCLUDED.embedding,
                   category=EXCLUDED.category, tags=EXCLUDED.tags,
                   importance=EXCLUDED.importance, updated_at=EXCLUDED.updated_at,
                   source_agent=EXCLUDED.source_agent, metadata=EXCLUDED.metadata""",
                memory.id, memory.content,
                memory.embedding if memory.embedding else None,
                memory.category, json.dumps(memory.tags), memory.importance,
                memory.created_at, memory.updated_at,
                memory.source_agent, json.dumps(memory.metadata),
            )
        return memory.id

    async def search(
        self, embedding: list[float], limit: int, filters: dict
    ) -> list[Memory]:
        from pgvector.asyncpg import register_vector

        conditions = ["embedding IS NOT NULL"]
        params: list = [str(embedding), limit]
        idx = 3
        if "category" in filters:
            conditions.append(f"category = ${idx}")
            params.append(filters["category"])
            idx += 1
        where = " AND ".join(conditions)
        async with self._pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                f"""SELECT * FROM memories WHERE {where}
                    ORDER BY embedding <=> $1
                    LIMIT $2""",
                *params,
            )
        return [self._row_to_memory(r) for r in rows]

    async def get(self, id: str) -> Memory | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM memories WHERE id = $1", id)
        return self._row_to_memory(row) if row else None

    async def delete(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM memories WHERE id = $1", id)
        return result == "DELETE 1"

    async def list(
        self, category: str | None, tags: list[str], limit: int
    ) -> list[Memory]:
        conditions = ["1=1"]
        params: list = [limit]
        idx = 2
        if category:
            conditions.append(f"category = ${idx}")
            params.append(category)
            idx += 1
        where = " AND ".join(conditions)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT $1",
                *params,
            )
        return [self._row_to_memory(r) for r in rows]

    def _row_to_memory(self, row) -> Memory:
        tags = row["tags"]
        if isinstance(tags, str):
            tags = json.loads(tags)
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return Memory(
            id=row["id"], content=row["content"], category=row["category"],
            tags=tags, importance=row["importance"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            source_agent=row["source_agent"], metadata=metadata,
        )

    async def store_chunk(self, chunk: IndexedChunk) -> str:
        from pgvector.asyncpg import register_vector

        async with self._pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute(
                """INSERT INTO indexed_chunks (id, source_path, chunk_index, content,
                   embedding, indexed_at, file_modified_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   ON CONFLICT (id) DO UPDATE SET
                   content=EXCLUDED.content, embedding=EXCLUDED.embedding,
                   indexed_at=EXCLUDED.indexed_at, file_modified_at=EXCLUDED.file_modified_at""",
                chunk.id, chunk.source_path, chunk.chunk_index, chunk.content,
                chunk.embedding, chunk.indexed_at, chunk.file_modified_at,
            )
        return chunk.id

    async def search_chunks(
        self, embedding: list[float], limit: int
    ) -> list[IndexedChunk]:
        from pgvector.asyncpg import register_vector

        async with self._pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """SELECT * FROM indexed_chunks
                   WHERE embedding IS NOT NULL
                   ORDER BY embedding <=> $1 LIMIT $2""",
                str(embedding), limit,
            )
        return [
            IndexedChunk(
                id=r["id"], source_path=r["source_path"],
                chunk_index=r["chunk_index"], content=r["content"],
                indexed_at=r["indexed_at"], file_modified_at=r["file_modified_at"],
            )
            for r in rows
        ]

    async def get_chunks_by_path(self, source_path: str) -> list[IndexedChunk]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM indexed_chunks WHERE source_path = $1 ORDER BY chunk_index",
                source_path,
            )
        return [
            IndexedChunk(
                id=r["id"], source_path=r["source_path"],
                chunk_index=r["chunk_index"], content=r["content"],
                indexed_at=r["indexed_at"], file_modified_at=r["file_modified_at"],
            )
            for r in rows
        ]

    async def delete_chunks_by_path(self, source_path: str) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM indexed_chunks WHERE source_path = $1", source_path
            )
        return int(result.split()[-1])
