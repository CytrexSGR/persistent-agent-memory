from __future__ import annotations

import time
from datetime import datetime

from persistent_agent_memory.models import Memory
from persistent_agent_memory.embeddings.base import EmbeddingProvider
from persistent_agent_memory.storage.base import StorageBackend


class MemoryService:
    def __init__(
        self,
        store: StorageBackend,
        embeddings: EmbeddingProvider,
        bootstrap_cache_ttl: int = 3600,
        source_agent: str = "",
    ):
        self._store = store
        self._embeddings = embeddings
        self._bootstrap_cache_ttl = bootstrap_cache_ttl
        self._source_agent = source_agent
        self._bootstrap_cache: dict | None = None
        self._bootstrap_cache_time: float = 0

    async def remember(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        importance: int = 3,
        metadata: dict | None = None,
    ) -> dict:
        embedding = await self._embeddings.embed(content)
        memory = Memory(
            content=content,
            embedding=embedding,
            category=category,
            tags=tags or [],
            importance=importance,
            source_agent=self._source_agent,
            metadata=metadata or {},
        )
        await self._store.store(memory)
        self._invalidate_bootstrap_cache()
        return self._memory_to_dict(memory)

    async def recall(
        self,
        query: str,
        limit: int = 10,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        embedding = await self._embeddings.embed(query)
        filters = {}
        if category:
            filters["category"] = category
        if tags:
            filters["tags"] = tags
        memories = await self._store.search(embedding=embedding, limit=limit, filters=filters)
        return [self._memory_to_dict(m) for m in memories]

    async def forget(self, memory_id: str) -> bool:
        deleted = await self._store.delete(memory_id)
        if deleted:
            self._invalidate_bootstrap_cache()
        return deleted

    async def remember_decision(
        self, decision: str, context: str, rationale: str
    ) -> dict:
        content = f"DECISION: {decision}\nCONTEXT: {context}\nRATIONALE: {rationale}"
        return await self.remember(
            content=content, category="decision", importance=5, tags=["decision"],
        )

    async def remember_rule(self, rule: str, reason: str) -> dict:
        content = f"RULE: {rule}\nREASON: {reason}"
        return await self.remember(
            content=content, category="rule", importance=5, tags=["rule"],
        )

    async def search_knowledge(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        return await self.recall(query=query, limit=limit, category=category, tags=tags)

    async def get_context(self, topic: str, limit: int = 10) -> dict:
        results = await self.recall(query=topic, limit=limit)
        return {"topic": topic, "memories": results, "count": len(results)}

    async def get_session_summary(self, limit: int = 20) -> list[dict]:
        memories = await self._store.list(category=None, tags=[], limit=limit)
        return [self._memory_to_dict(m) for m in memories]

    async def get_bootstrap_context(self) -> dict:
        now = time.time()
        if (
            self._bootstrap_cache is not None
            and (now - self._bootstrap_cache_time) < self._bootstrap_cache_ttl
        ):
            return self._bootstrap_cache

        decisions = await self._store.list(category="decision", tags=[], limit=20)
        rules = await self._store.list(category="rule", tags=[], limit=20)
        handoffs = await self._store.list(category="handoff", tags=[], limit=10)
        recent = await self._store.list(category=None, tags=[], limit=10)

        ctx = {
            "decisions": [self._memory_to_dict(m) for m in decisions],
            "rules": [self._memory_to_dict(m) for m in rules],
            "handoffs": [self._memory_to_dict(m) for m in handoffs],
            "recent": [self._memory_to_dict(m) for m in recent],
        }
        self._bootstrap_cache = ctx
        self._bootstrap_cache_time = now
        return ctx

    def _invalidate_bootstrap_cache(self) -> None:
        self._bootstrap_cache = None
        self._bootstrap_cache_time = 0

    @staticmethod
    def _memory_to_dict(memory: Memory) -> dict:
        created = memory.created_at
        if isinstance(created, datetime):
            created = created.isoformat()
        return {
            "id": memory.id,
            "content": memory.content,
            "category": memory.category,
            "tags": memory.tags,
            "importance": memory.importance,
            "created_at": str(created),
            "source_agent": memory.source_agent,
            "metadata": memory.metadata,
        }
