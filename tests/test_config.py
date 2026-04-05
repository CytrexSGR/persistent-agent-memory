import pytest
from persistent_agent_memory.config import Settings


def test_default_settings():
    """Default settings use sqlite + api embedding provider."""
    s = Settings(
        EMBEDDING_API_URL="http://localhost:11434/v1",
        EMBEDDING_MODEL="nomic-embed-text",
    )
    assert s.STORAGE_BACKEND == "sqlite"
    assert s.EMBEDDING_PROVIDER == "api"
    assert s.SQLITE_PATH == "./data/memory.db"
    assert s.EMBEDDING_DIMENSIONS == 768
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8765
    assert s.BOOTSTRAP_CACHE_TTL == 3600


def test_postgres_settings():
    """Postgres backend requires DATABASE_URL."""
    s = Settings(
        STORAGE_BACKEND="postgres",
        DATABASE_URL="postgresql://user:pass@localhost/mem",
        EMBEDDING_API_URL="http://localhost:11434/v1",
        EMBEDDING_MODEL="nomic-embed-text",
    )
    assert s.STORAGE_BACKEND == "postgres"
    assert s.DATABASE_URL == "postgresql://user:pass@localhost/mem"


def test_local_embedding_settings():
    """Local embedding provider settings."""
    s = Settings(
        EMBEDDING_PROVIDER="local",
        LOCAL_MODEL="all-MiniLM-L6-v2",
        LOCAL_DEVICE="cpu",
        EMBEDDING_API_URL="http://unused",
        EMBEDDING_MODEL="unused",
    )
    assert s.EMBEDDING_PROVIDER == "local"
    assert s.LOCAL_MODEL == "all-MiniLM-L6-v2"
    assert s.LOCAL_DEVICE == "cpu"


def test_invalid_storage_backend():
    """Invalid backend raises validation error."""
    with pytest.raises(Exception):
        Settings(
            STORAGE_BACKEND="mongodb",
            EMBEDDING_API_URL="http://localhost:11434/v1",
            EMBEDDING_MODEL="nomic-embed-text",
        )
