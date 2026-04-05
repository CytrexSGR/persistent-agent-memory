from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path

import sqlite_vec

from persistent_agent_memory.models import Memory, IndexedChunk
from .base import StorageBackend


class SqliteStore(StorageBackend):
    def __init__(self, db_path: str, dimensions: int):
        self._db_path = db_path
        self._dimensions = dimensions
        self._conn: sqlite3.Connection | None = None

    def _serialize_vec(self, vec: list[float]) -> bytes:
        return struct.pack(f"{len(vec)}f", *vec)

    async def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                tags TEXT NOT NULL DEFAULT '[]',
                importance INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_agent TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        self._conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_vectors USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[{self._dimensions}]
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS indexed_chunks (
                id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                file_modified_at TEXT
            )
        """)
        self._conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[{self._dimensions}]
            )
        """)
        self._conn.commit()

    async def store(self, memory: Memory) -> str:
        self._conn.execute(
            """INSERT OR REPLACE INTO memories
               (id, content, category, tags, importance, created_at, updated_at, source_agent, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id, memory.content, memory.category,
                json.dumps(memory.tags), memory.importance,
                memory.created_at.isoformat() if hasattr(memory.created_at, 'isoformat') else str(memory.created_at),
                memory.updated_at.isoformat() if hasattr(memory.updated_at, 'isoformat') else str(memory.updated_at),
                memory.source_agent, json.dumps(memory.metadata),
            ),
        )
        if memory.embedding:
            # Delete existing vector first (vec0 doesn't support OR REPLACE)
            self._conn.execute("DELETE FROM memory_vectors WHERE id = ?", (memory.id,))
            self._conn.execute(
                "INSERT INTO memory_vectors (id, embedding) VALUES (?, ?)",
                (memory.id, self._serialize_vec(memory.embedding)),
            )
        self._conn.commit()
        return memory.id

    async def search(
        self, embedding: list[float], limit: int, filters: dict
    ) -> list[Memory]:
        rows = self._conn.execute(
            """SELECT v.id, v.distance
               FROM memory_vectors v
               WHERE embedding MATCH ?
               ORDER BY distance
               LIMIT ?""",
            (self._serialize_vec(embedding), limit * 3),
        ).fetchall()

        results = []
        for row_id, distance in rows:
            mem = await self.get(row_id)
            if mem is None:
                continue
            if "category" in filters and mem.category != filters["category"]:
                continue
            if "tags" in filters:
                if not any(t in mem.tags for t in filters["tags"]):
                    continue
            results.append(mem)
            if len(results) >= limit:
                break
        return results

    async def get(self, id: str) -> Memory | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            return None
        return Memory(
            id=row[0], content=row[1], category=row[2],
            tags=json.loads(row[3]), importance=row[4],
            created_at=row[5], updated_at=row[6],
            source_agent=row[7], metadata=json.loads(row[8]),
        )

    async def delete(self, id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM memories WHERE id = ?", (id,))
        self._conn.execute("DELETE FROM memory_vectors WHERE id = ?", (id,))
        self._conn.commit()
        return cursor.rowcount > 0

    async def list(
        self, category: str | None, tags: list[str], limit: int
    ) -> list[Memory]:
        query = "SELECT * FROM memories WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            mem = Memory(
                id=row[0], content=row[1], category=row[2],
                tags=json.loads(row[3]), importance=row[4],
                created_at=row[5], updated_at=row[6],
                source_agent=row[7], metadata=json.loads(row[8]),
            )
            if tags and not any(t in mem.tags for t in tags):
                continue
            results.append(mem)
        return results

    async def store_chunk(self, chunk: IndexedChunk) -> str:
        self._conn.execute(
            """INSERT OR REPLACE INTO indexed_chunks
               (id, source_path, chunk_index, content, indexed_at, file_modified_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                chunk.id, chunk.source_path, chunk.chunk_index, chunk.content,
                chunk.indexed_at.isoformat() if hasattr(chunk.indexed_at, 'isoformat') else str(chunk.indexed_at),
                chunk.file_modified_at.isoformat() if chunk.file_modified_at and hasattr(chunk.file_modified_at, 'isoformat') else None,
            ),
        )
        if chunk.embedding:
            self._conn.execute("DELETE FROM chunk_vectors WHERE id = ?", (chunk.id,))
            self._conn.execute(
                "INSERT INTO chunk_vectors (id, embedding) VALUES (?, ?)",
                (chunk.id, self._serialize_vec(chunk.embedding)),
            )
        self._conn.commit()
        return chunk.id

    async def search_chunks(
        self, embedding: list[float], limit: int
    ) -> list[IndexedChunk]:
        rows = self._conn.execute(
            """SELECT v.id, v.distance
               FROM chunk_vectors v
               WHERE embedding MATCH ?
               ORDER BY distance
               LIMIT ?""",
            (self._serialize_vec(embedding), limit),
        ).fetchall()
        results = []
        for row_id, _ in rows:
            row = self._conn.execute(
                "SELECT * FROM indexed_chunks WHERE id = ?", (row_id,)
            ).fetchone()
            if row:
                results.append(IndexedChunk(
                    id=row[0], source_path=row[1], chunk_index=row[2],
                    content=row[3], indexed_at=row[4], file_modified_at=row[5],
                ))
        return results

    async def get_chunks_by_path(self, source_path: str) -> list[IndexedChunk]:
        rows = self._conn.execute(
            "SELECT * FROM indexed_chunks WHERE source_path = ? ORDER BY chunk_index",
            (source_path,),
        ).fetchall()
        return [
            IndexedChunk(
                id=r[0], source_path=r[1], chunk_index=r[2],
                content=r[3], indexed_at=r[4], file_modified_at=r[5],
            )
            for r in rows
        ]

    async def delete_chunks_by_path(self, source_path: str) -> int:
        chunk_ids = [
            r[0] for r in self._conn.execute(
                "SELECT id FROM indexed_chunks WHERE source_path = ?", (source_path,)
            ).fetchall()
        ]
        for cid in chunk_ids:
            self._conn.execute("DELETE FROM chunk_vectors WHERE id = ?", (cid,))
        cursor = self._conn.execute(
            "DELETE FROM indexed_chunks WHERE source_path = ?", (source_path,)
        )
        self._conn.commit()
        return cursor.rowcount
