import json
import pytest
import httpx

from persistent_agent_memory.embeddings.api_provider import ApiEmbeddingProvider


class MockTransport(httpx.AsyncBaseTransport):
    """Mock transport that returns fake embeddings."""

    def __init__(self, dimensions: int = 768):
        self.dimensions = dimensions
        self.requests = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = json.loads(request.content)
        inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
        data = [
            {"object": "embedding", "index": i, "embedding": [0.1] * self.dimensions}
            for i in range(len(inputs))
        ]
        return httpx.Response(
            200,
            json={"object": "list", "data": data, "model": body["model"]},
        )


@pytest.fixture
def mock_transport():
    return MockTransport(dimensions=768)


@pytest.fixture
def provider(mock_transport):
    client = httpx.AsyncClient(transport=mock_transport, base_url="http://test")
    return ApiEmbeddingProvider(
        api_url="http://test/v1",
        model="nomic-embed-text",
        dimensions=768,
        client=client,
    )


async def test_embed_single(provider):
    result = await provider.embed("hello world")
    assert len(result) == 768
    assert all(isinstance(v, float) for v in result)


async def test_embed_batch(provider):
    results = await provider.embed_batch(["hello", "world"])
    assert len(results) == 2
    assert len(results[0]) == 768


async def test_dimensions_property(provider):
    assert provider.dimensions == 768


async def test_sends_correct_payload(provider, mock_transport):
    await provider.embed("test text")
    assert len(mock_transport.requests) == 1
    body = json.loads(mock_transport.requests[0].content)
    assert body["model"] == "nomic-embed-text"
    assert body["input"] == "test text"
