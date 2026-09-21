"""Tests for RAPTOR hierarchical chunker."""

import pytest

from app.chunkers.base import Chunk, ChunkingConfig
from app.chunkers.raptor import RAPTORChunker


@pytest.fixture
def default_config():
    """Create default chunking config."""
    return ChunkingConfig(chunk_size=200, chunk_overlap=0, min_chunk_size=10)


@pytest.fixture
def raptor(default_config):
    """Create a RAPTOR chunker without LLM (sync mode)."""
    return RAPTORChunker(config=default_config)


@pytest.fixture
def sample_text():
    """Sample text for chunking tests."""
    return (
        "Python is a high-level programming language. "
        "It was created by Guido van Rossum. "
        "Python emphasizes code readability and simplicity.\n\n"
        "JavaScript is the language of the web. "
        "It runs in browsers and on servers via Node.js. "
        "JavaScript supports event-driven programming.\n\n"
        "Rust is a systems programming language. "
        "It focuses on safety, speed, and concurrency. "
        "Rust prevents many common bugs at compile time."
    )


# ------------------------------------------------------------------
# Synchronous chunk (leaf level)
# ------------------------------------------------------------------


def test_chunk_returns_leaf_chunks(raptor, sample_text):
    """Test that sync chunk produces leaf-level chunks."""
    chunks = raptor.chunk(sample_text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, Chunk)
        assert chunk.metadata.get("tree_level") == 0
        assert chunk.metadata.get("parent_chunk_id") is None


def test_chunk_empty_text(raptor):
    """Test that empty text returns no chunks."""
    chunks = raptor.chunk("")
    assert chunks == []


def test_chunk_respects_min_size(default_config):
    """Test that chunks smaller than min_chunk_size are filtered."""
    config = ChunkingConfig(chunk_size=200, chunk_overlap=0, min_chunk_size=50)
    raptor = RAPTORChunker(config=config)
    chunks = raptor.chunk("Hi.")
    # "Hi." is 3 chars, below min_chunk_size of 50
    assert len(chunks) == 0


def test_chunk_preserves_content(raptor, sample_text):
    """Test that combined chunk content covers the original text."""
    chunks = raptor.chunk(sample_text)
    combined = " ".join(c.content for c in chunks)
    # Key phrases should be present
    assert "Python" in combined
    assert "JavaScript" in combined
    assert "Rust" in combined


def test_chunk_has_content_hash(raptor, sample_text):
    """Test that chunks have content hashes."""
    chunks = raptor.chunk(sample_text)
    for chunk in chunks:
        assert chunk.content_hash != ""


def test_chunk_with_custom_metadata(raptor, sample_text):
    """Test that custom metadata is passed through."""
    chunks = raptor.chunk(sample_text, metadata={"source": "test.txt"})
    for chunk in chunks:
        assert chunk.metadata.get("source") == "test.txt"
        assert chunk.metadata.get("tree_level") == 0


# ------------------------------------------------------------------
# Async chunk (full RAPTOR tree)
# ------------------------------------------------------------------


async def test_chunk_async_builds_tree(sample_text):
    """Test async RAPTOR tree building with mock LLM."""

    async def mock_llm_generate(prompt: str) -> str:
        return "This is a summary of the cluster about programming languages."

    config = ChunkingConfig(chunk_size=200, chunk_overlap=0, min_chunk_size=10)
    raptor = RAPTORChunker(
        config=config,
        max_tree_levels=2,
        cluster_size=2,
        llm_generate=mock_llm_generate,
    )

    chunks = await raptor.chunk_async(sample_text)
    assert len(chunks) > 0

    # Should have multiple levels
    levels = {c.metadata.get("tree_level", 0) for c in chunks}
    assert 0 in levels  # leaf level always present
    # With enough text and cluster_size=2, should produce at least level 1
    if len([c for c in chunks if c.metadata.get("tree_level") == 0]) > 1:
        assert len(levels) > 1


async def test_chunk_async_without_llm_falls_back(sample_text):
    """Test async chunk without LLM returns leaf chunks only."""
    config = ChunkingConfig(chunk_size=200, chunk_overlap=0, min_chunk_size=10)
    raptor = RAPTORChunker(config=config)

    chunks = await raptor.chunk_async(sample_text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.metadata.get("tree_level") == 0


async def test_chunk_async_with_embeddings(sample_text):
    """Test RAPTOR with embedding-based clustering."""

    async def mock_llm_generate(prompt: str) -> str:
        return "Summary of programming concepts."

    async def mock_embed_texts(texts):
        # Return simple mock embeddings (2D for simplicity)
        import math

        return [[math.sin(i * 0.5), math.cos(i * 0.5)] for i in range(len(texts))]

    config = ChunkingConfig(chunk_size=200, chunk_overlap=0, min_chunk_size=10)
    raptor = RAPTORChunker(
        config=config,
        max_tree_levels=1,
        cluster_size=2,
        llm_generate=mock_llm_generate,
        embed_texts=mock_embed_texts,
    )

    chunks = await raptor.chunk_async(sample_text)
    assert len(chunks) > 0


async def test_chunk_async_empty_text():
    """Test async chunk with empty text."""
    raptor = RAPTORChunker()
    chunks = await raptor.chunk_async("")
    assert chunks == []


async def test_chunk_async_single_chunk():
    """Test async chunk when text fits in a single chunk."""

    async def mock_llm_generate(prompt: str) -> str:
        return "Short summary."

    config = ChunkingConfig(chunk_size=5000, chunk_overlap=0, min_chunk_size=10)
    raptor = RAPTORChunker(
        config=config,
        llm_generate=mock_llm_generate,
    )

    chunks = await raptor.chunk_async("Short text about Python.")
    assert len(chunks) >= 1


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def test_simple_kmeans():
    """Test the minimal k-means implementation."""
    vectors = [
        [0.0, 0.0],
        [0.1, 0.1],
        [10.0, 10.0],
        [10.1, 10.1],
    ]
    assignments = RAPTORChunker._simple_kmeans(vectors, k=2)
    assert len(assignments) == 4
    # First two should be in same cluster, last two in another
    assert assignments[0] == assignments[1]
    assert assignments[2] == assignments[3]
    assert assignments[0] != assignments[2]


def test_simple_kmeans_edge_cases():
    """Test k-means with edge cases."""
    assert RAPTORChunker._simple_kmeans([], k=2) == []
    assert RAPTORChunker._simple_kmeans([[1, 2]], k=5) == [0]


def test_cluster_sequential(raptor, sample_text):
    """Test sequential clustering fallback."""
    chunks = raptor.chunk(sample_text)
    clusters = raptor._cluster_sequential(chunks)
    assert len(clusters) > 0
    # All chunks should be present
    total = sum(len(c) for c in clusters)
    assert total == len(chunks)


# ------------------------------------------------------------------
# Factory integration
# ------------------------------------------------------------------


def test_raptor_in_factory():
    """Test that RAPTOR is registered in the chunker factory."""
    from app.chunkers.factory import ChunkingStrategy, get_chunker

    chunker = get_chunker(ChunkingStrategy.RAPTOR)
    assert isinstance(chunker, RAPTORChunker)


def test_raptor_from_string():
    """Test creating RAPTOR chunker from string strategy."""
    from app.chunkers.factory import get_chunker

    chunker = get_chunker("raptor")
    assert isinstance(chunker, RAPTORChunker)
