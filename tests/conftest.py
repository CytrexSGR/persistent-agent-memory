import pytest

from persistent_agent_memory.config import Settings


@pytest.fixture
def tmp_db(tmp_path):
    """Return path to a temporary SQLite database."""
    return str(tmp_path / "test_memory.db")


@pytest.fixture
def settings(tmp_db):
    """Settings pointing to temp database with mock embedding URL."""
    return Settings(
        SQLITE_PATH=tmp_db,
        EMBEDDING_API_URL="http://localhost:11434/v1",
        EMBEDDING_MODEL="nomic-embed-text",
        EMBEDDING_DIMENSIONS=768,
    )


class FakeEmbeddingProvider:
    """Returns deterministic embeddings for testing."""

    def __init__(self, dimensions: int = 768):
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Hash-based deterministic embedding."""
        import hashlib

        h = hashlib.sha256(text.encode()).digest()
        vec = [b / 255.0 for b in h]
        vec = (vec * ((self._dimensions // len(vec)) + 1))[: self._dimensions]
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._dimensions


@pytest.fixture
def fake_embeddings():
    return FakeEmbeddingProvider()
