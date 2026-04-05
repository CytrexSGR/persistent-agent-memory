from __future__ import annotations

import httpx

from .base import EmbeddingProvider


class ApiEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible /v1/embeddings provider."""

    def __init__(
        self,
        api_url: str,
        model: str,
        dimensions: int,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_url = api_url.rstrip("/")
        self._model = model
        self._dimensions = dimensions
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = client or httpx.AsyncClient(
            base_url=self._api_url,
            headers=headers,
            timeout=30.0,
        )
        self._owns_client = client is None

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.post(
            "/v1/embeddings",
            json={"model": self._model, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            "/v1/embeddings",
            json={"model": self._model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]

    @property
    def dimensions(self) -> int:
        return self._dimensions
