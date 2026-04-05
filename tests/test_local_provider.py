import pytest

from persistent_agent_memory.embeddings.local_provider import LocalEmbeddingProvider


@pytest.fixture
def provider():
    try:
        return LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2", device="cpu")
    except (ImportError, ModuleNotFoundError):
        pytest.skip("sentence-transformers not installed")


async def test_embed_single(provider):
    result = await provider.embed("hello world")
    assert len(result) == provider.dimensions
    assert all(isinstance(v, float) for v in result)


async def test_embed_batch(provider):
    results = await provider.embed_batch(["hello", "world", "test"])
    assert len(results) == 3
    for r in results:
        assert len(r) == provider.dimensions


async def test_dimensions(provider):
    assert provider.dimensions == 384


async def test_different_texts_different_embeddings(provider):
    a = await provider.embed("the cat sat on the mat")
    b = await provider.embed("quantum chromodynamics in particle physics")
    assert a != b
