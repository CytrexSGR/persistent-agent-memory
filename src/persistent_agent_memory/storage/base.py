from __future__ import annotations

from abc import ABC, abstractmethod

from persistent_agent_memory.models import Memory, IndexedChunk


class StorageBackend(ABC):
    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def store(self, memory: Memory) -> str: ...

    @abstractmethod
    async def search(
        self, embedding: list[float], limit: int, filters: dict
    ) -> list[Memory]: ...

    @abstractmethod
    async def get(self, id: str) -> Memory | None: ...

    @abstractmethod
    async def delete(self, id: str) -> bool: ...

    @abstractmethod
    async def list(
        self, category: str | None, tags: list[str], limit: int
    ) -> list[Memory]: ...

    @abstractmethod
    async def store_chunk(self, chunk: IndexedChunk) -> str: ...

    @abstractmethod
    async def search_chunks(
        self, embedding: list[float], limit: int
    ) -> list[IndexedChunk]: ...

    @abstractmethod
    async def get_chunks_by_path(self, source_path: str) -> list[IndexedChunk]: ...

    @abstractmethod
    async def delete_chunks_by_path(self, source_path: str) -> int: ...
