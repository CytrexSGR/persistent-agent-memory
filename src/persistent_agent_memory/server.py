from __future__ import annotations

import json
import sys

from mcp.server.fastmcp import FastMCP

from persistent_agent_memory.config import Settings
from persistent_agent_memory.service import MemoryService
from persistent_agent_memory.indexer import DirectoryIndexer
from persistent_agent_memory.embeddings.base import EmbeddingProvider
from persistent_agent_memory.storage.base import StorageBackend


def create_app(
    settings: Settings | None = None,
    store: StorageBackend | None = None,
    embeddings: EmbeddingProvider | None = None,
) -> FastMCP:
    settings = settings or Settings()
    mcp = FastMCP("persistent-agent-memory")

    _service: MemoryService | None = None
    _indexer: DirectoryIndexer | None = None

    async def get_service() -> MemoryService:
        nonlocal _service, store, embeddings
        if _service is not None:
            return _service

        if embeddings is None:
            if settings.EMBEDDING_PROVIDER == "local":
                from persistent_agent_memory.embeddings.local_provider import LocalEmbeddingProvider
                embeddings = LocalEmbeddingProvider(
                    model_name=settings.LOCAL_MODEL, device=settings.LOCAL_DEVICE,
                )
            else:
                from persistent_agent_memory.embeddings.api_provider import ApiEmbeddingProvider
                embeddings = ApiEmbeddingProvider(
                    api_url=settings.EMBEDDING_API_URL,
                    model=settings.EMBEDDING_MODEL,
                    dimensions=settings.EMBEDDING_DIMENSIONS,
                    api_key=settings.EMBEDDING_API_KEY,
                )

        if store is None:
            if settings.STORAGE_BACKEND == "postgres":
                from persistent_agent_memory.storage.postgres_store import PostgresStore
                store = PostgresStore(settings.DATABASE_URL, settings.EMBEDDING_DIMENSIONS)
            else:
                from persistent_agent_memory.storage.sqlite_store import SqliteStore
                store = SqliteStore(settings.SQLITE_PATH, settings.EMBEDDING_DIMENSIONS)
            await store.initialize()

        _service = MemoryService(
            store=store, embeddings=embeddings,
            bootstrap_cache_ttl=settings.BOOTSTRAP_CACHE_TTL,
        )
        return _service

    async def get_indexer() -> DirectoryIndexer:
        nonlocal _indexer
        if _indexer is None:
            svc = await get_service()
            _indexer = DirectoryIndexer(store=svc._store, embeddings=svc._embeddings)
        return _indexer

    @mcp.tool()
    async def remember(
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
        importance: int = 3,
    ) -> str:
        """Store a memory with content, category, tags, and importance (1-5)."""
        svc = await get_service()
        result = await svc.remember(
            content=content, category=category, tags=tags or [], importance=importance,
        )
        return json.dumps(result)

    @mcp.tool()
    async def recall(
        query: str,
        limit: int = 10,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Semantic search for memories via natural language query."""
        svc = await get_service()
        results = await svc.recall(query=query, limit=limit, category=category, tags=tags)
        return json.dumps(results)

    @mcp.tool()
    async def forget(memory_id: str) -> str:
        """Delete a memory by ID."""
        svc = await get_service()
        deleted = await svc.forget(memory_id)
        return json.dumps({"deleted": deleted, "id": memory_id})

    @mcp.tool()
    async def remember_decision(decision: str, context: str, rationale: str) -> str:
        """Store an architecture decision with context and rationale."""
        svc = await get_service()
        result = await svc.remember_decision(decision, context, rationale)
        return json.dumps(result)

    @mcp.tool()
    async def remember_rule(rule: str, reason: str) -> str:
        """Store a rule or constraint that must be followed."""
        svc = await get_service()
        result = await svc.remember_rule(rule, reason)
        return json.dumps(result)

    @mcp.tool()
    async def search_knowledge(
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Extended search with similarity threshold and filters."""
        svc = await get_service()
        results = await svc.search_knowledge(
            query=query, limit=limit, threshold=threshold,
            category=category, tags=tags,
        )
        return json.dumps(results)

    @mcp.tool()
    async def get_context(topic: str, limit: int = 10) -> str:
        """Load context for a topic — recall and summarize relevant memories."""
        svc = await get_service()
        result = await svc.get_context(topic=topic, limit=limit)
        return json.dumps(result)

    @mcp.tool()
    async def get_session_summary(limit: int = 20) -> str:
        """Get the last N memories as a session briefing."""
        svc = await get_service()
        results = await svc.get_session_summary(limit=limit)
        return json.dumps(results)

    @mcp.tool()
    async def get_bootstrap_context() -> str:
        """Load everything an agent needs at session start (decisions, rules, handoffs, recent). Cached."""
        svc = await get_service()
        result = await svc.get_bootstrap_context()
        return json.dumps(result)

    @mcp.tool()
    async def index_directory(path: str, glob: str = "**/*.md") -> str:
        """Scan a directory of files, chunk, embed, and store for semantic search."""
        idx = await get_indexer()
        result = await idx.index_directory(path=path, glob=glob)
        return json.dumps(result)

    @mcp.tool()
    async def search_indexed(query: str, limit: int = 10) -> str:
        """Semantic search over indexed files (separate from memories)."""
        idx = await get_indexer()
        results = await idx.search(query=query, limit=limit)
        return json.dumps(results)

    return mcp


def main():
    """CLI entry point: pam serve."""
    mcp = create_app()
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        if "--stdio" in sys.argv:
            mcp.run(transport="stdio")
        else:
            settings = Settings()
            mcp.run(transport="sse", host=settings.HOST, port=settings.PORT)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
