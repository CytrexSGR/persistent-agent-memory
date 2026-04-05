from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    # Storage
    STORAGE_BACKEND: Literal["sqlite", "postgres"] = "sqlite"
    SQLITE_PATH: str = "./data/memory.db"
    DATABASE_URL: str | None = None

    # Embeddings
    EMBEDDING_PROVIDER: Literal["api", "local"] = "api"
    EMBEDDING_API_URL: str = "http://localhost:11434/v1"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 768
    EMBEDDING_API_KEY: str | None = None

    # Local GPU
    LOCAL_MODEL: str = "all-MiniLM-L6-v2"
    LOCAL_DEVICE: str = "cuda"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8765

    # Bootstrap
    BOOTSTRAP_CACHE_TTL: int = 3600
