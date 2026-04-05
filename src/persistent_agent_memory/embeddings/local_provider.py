from __future__ import annotations

import asyncio
from functools import partial

from .base import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers provider for local GPU/CPU embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cuda"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)
        self._dimensions = self._model.get_sentence_embedding_dimension()

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, partial(self._model.encode, text, normalize_embeddings=True)
        )
        return result.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, partial(self._model.encode, texts, normalize_embeddings=True)
        )
        return results.tolist()

    @property
    def dimensions(self) -> int:
        return self._dimensions
