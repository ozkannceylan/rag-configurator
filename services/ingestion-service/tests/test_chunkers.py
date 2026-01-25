"""Tests for text chunkers."""

import pytest

from app.chunkers.base import Chunk, ChunkingConfig
from app.chunkers.document import DocumentChunker, FixedSizeChunker, ParagraphChunker
from app.chunkers.factory import (
    ChunkingStrategy,
    get_available_strategies,
    get_chunker,
    get_default_config,
)
from app.chunkers.recursive import RecursiveChunker
from app.chunkers.semantic import SemanticChunker


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_chunk_creation(self):
        """Test basic chunk creation."""
        chunk = Chunk(content="Hello world", chunk_index=0)
        assert chunk.content == "Hello world"
        assert chunk.chunk_index == 0
        assert chunk.content_hash != ""

    def test_chunk_word_count(self):
        """Test word count calculation."""
        chunk = Chunk(content="Hello world how are you")
        assert chunk.word_count == 5

    def test_chunk_char_count(self):
        """Test character count."""
        chunk = Chunk(content="Hello")
        assert chunk.char_count == 5

    def test_chunk_hash_generation(self):
        """Test content hash is generated."""
        chunk1 = Chunk(content="Hello world")
        chunk2 = Chunk(content="Hello world")
        chunk3 = Chunk(content="Different content")

        assert chunk1.content_hash == chunk2.content_hash
        assert chunk1.content_hash != chunk3.content_hash

    def test_chunk_to_dict(self):
        """Test conversion to dictionary."""
        chunk = Chunk(
            content="Test content",
            chunk_index=1,
            start_char=10,
            end_char=22,
        )
        result = chunk.to_dict()

        assert result["content"] == "Test content"
        assert result["chunk_index"] == 1
        assert result["start_char"] == 10
        assert result["end_char"] == 22


class TestChunkingConfig:
    """Tests for ChunkingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.min_chunk_size == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ChunkingConfig(
            chunk_size=500,
            chunk_overlap=50,
            min_chunk_size=20,
        )

        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.min_chunk_size == 20

    def test_validation_chunk_size(self):
        """Test validation of chunk_size."""
        config = ChunkingConfig(chunk_size=0)
        with pytest.raises(ValueError):
            config.validate()

    def test_validation_overlap(self):
        """Test validation of chunk_overlap."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=100)
        with pytest.raises(ValueError):
            config.validate()


class TestRecursiveChunker:
    """Tests for RecursiveChunker."""

    @pytest.fixture
    def chunker(self):
        """Create recursive chunker instance."""
        return RecursiveChunker()

    @pytest.fixture
    def sample_text(self):
        """Create sample text for testing."""
        return """This is the first paragraph. It has multiple sentences. This is the third sentence.

This is the second paragraph. It also has content.

This is the third paragraph with even more text to process."""

    def test_chunk_simple_text(self, chunker):
        """Test chunking simple text."""
        text = "Hello world. This is a test."
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_respects_size(self, chunker):
        """Test that chunks respect size limit."""
        config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
        chunker = RecursiveChunker(config)

        text = "A" * 200
        chunks = chunker.chunk(text)

        # All chunks should be within size limit (with some tolerance for overlap)
        for chunk in chunks:
            assert len(chunk.content) <= config.chunk_size + config.chunk_overlap

    def test_chunk_with_paragraphs(self, chunker, sample_text):
        """Test chunking text with paragraphs."""
        chunks = chunker.chunk(sample_text)

        assert len(chunks) >= 1
        # Content should be preserved
        combined = " ".join(c.content for c in chunks)
        assert "first paragraph" in combined

    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk("")
        assert chunks == []

    def test_chunk_with_metadata(self, chunker):
        """Test chunking with metadata."""
        text = "Hello world"
        metadata = {"source": "test", "author": "pytest"}
        chunks = chunker.chunk(text, metadata=metadata)

        assert len(chunks) >= 1
        assert chunks[0].metadata.get("source") == "test"


class TestSemanticChunker:
    """Tests for SemanticChunker."""

    @pytest.fixture
    def chunker(self):
        """Create semantic chunker instance."""
        return SemanticChunker()

    @pytest.fixture
    def multi_sentence_text(self):
        """Create text with multiple sentences."""
        return (
            "This is the first sentence. This is the second sentence. "
            "Here comes the third sentence. And finally the fourth one."
        )

    def test_chunk_by_sentences(self, chunker, multi_sentence_text):
        """Test that chunking respects sentence boundaries."""
        config = ChunkingConfig(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk(multi_sentence_text, config)

        assert len(chunks) >= 1
        # Sentences should not be cut in the middle
        for chunk in chunks:
            # Should end with sentence-ending punctuation or be complete
            content = chunk.content.strip()
            assert content[-1] in ".!?" or len(content) < 20

    def test_chunk_preserves_content(self, chunker):
        """Test that all content is preserved."""
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker.chunk(text)

        combined = " ".join(c.content for c in chunks)
        assert "First" in combined
        assert "Second" in combined
        assert "Third" in combined

    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk("")
        assert chunks == []

    def test_sentence_count_metadata(self, chunker):
        """Test sentence count in metadata."""
        text = "First sentence. Second sentence. Third sentence."
        config = ChunkingConfig(chunk_size=1000)  # Large size to get one chunk
        chunks = chunker.chunk(text, config)

        if chunks:
            assert "sentence_count" in chunks[0].metadata


class TestDocumentChunker:
    """Tests for DocumentChunker."""

    @pytest.fixture
    def chunker(self):
        """Create document chunker instance."""
        return DocumentChunker()

    def test_returns_single_chunk(self, chunker):
        """Test that entire document is returned as one chunk."""
        text = "This is a test document with multiple sentences. Here is another one."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text.strip()

    def test_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk("")
        assert chunks == []


class TestParagraphChunker:
    """Tests for ParagraphChunker."""

    @pytest.fixture
    def chunker(self):
        """Create paragraph chunker instance."""
        config = ChunkingConfig(min_chunk_size=10)
        return ParagraphChunker(config)

    def test_splits_by_paragraphs(self, chunker):
        """Test splitting by paragraphs."""
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph."
        chunks = chunker.chunk(text)

        assert len(chunks) == 3
        assert "First" in chunks[0].content
        assert "Second" in chunks[1].content
        assert "Third" in chunks[2].content


class TestFixedSizeChunker:
    """Tests for FixedSizeChunker."""

    @pytest.fixture
    def chunker(self):
        """Create fixed size chunker instance."""
        config = ChunkingConfig(chunk_size=50, chunk_overlap=10, min_chunk_size=5)
        return FixedSizeChunker(config)

    def test_fixed_size_chunks(self, chunker):
        """Test that chunks are approximately fixed size."""
        text = "A" * 200
        chunks = chunker.chunk(text)

        # Should have multiple chunks
        assert len(chunks) > 1

        # Each chunk (except last) should be close to chunk_size
        for chunk in chunks[:-1]:
            assert len(chunk.content) <= 50


class TestChunkerFactory:
    """Tests for chunker factory."""

    def test_get_recursive_chunker(self):
        """Test getting recursive chunker."""
        chunker = get_chunker(ChunkingStrategy.RECURSIVE)
        assert isinstance(chunker, RecursiveChunker)

    def test_get_semantic_chunker(self):
        """Test getting semantic chunker."""
        chunker = get_chunker(ChunkingStrategy.SEMANTIC)
        assert isinstance(chunker, SemanticChunker)

    def test_get_document_chunker(self):
        """Test getting document chunker."""
        chunker = get_chunker(ChunkingStrategy.DOCUMENT)
        assert isinstance(chunker, DocumentChunker)

    def test_get_chunker_by_string(self):
        """Test getting chunker by string name."""
        chunker = get_chunker("recursive")
        assert isinstance(chunker, RecursiveChunker)

    def test_get_chunker_with_config(self):
        """Test getting chunker with custom config."""
        config = ChunkingConfig(chunk_size=500)
        chunker = get_chunker(ChunkingStrategy.RECURSIVE, config)

        assert chunker.config.chunk_size == 500

    def test_invalid_strategy(self):
        """Test getting chunker with invalid strategy."""
        with pytest.raises(ValueError):
            get_chunker("invalid_strategy")

    def test_get_available_strategies(self):
        """Test getting available strategies."""
        strategies = get_available_strategies()

        assert "recursive" in strategies
        assert "semantic" in strategies
        assert "document" in strategies

    def test_get_default_config(self):
        """Test getting default config for strategy."""
        config = get_default_config(ChunkingStrategy.SEMANTIC)

        assert config.chunk_size == 1500
        assert config.combine_short_sentences is True
