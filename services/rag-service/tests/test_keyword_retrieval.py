"""Tests for keyword retrieval module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.retrieval.base import RetrievedChunk, SourceType
from app.retrieval.keyword import KeywordConfig, KeywordRetriever


class TestKeywordConfig:
    """Tests for KeywordConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = KeywordConfig()

        assert config.top_k == 10
        assert config.min_score == 0.0
        assert config.use_fuzzy is True
        assert config.max_edits == 1
        assert config.boost_factor == 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = KeywordConfig(
            top_k=20,
            min_score=0.3,
            use_fuzzy=False,
            max_edits=2,
            boost_factor=1.5,
            folder_paths=["/data"],
        )

        assert config.top_k == 20
        assert config.use_fuzzy is False
        assert config.boost_factor == 1.5
        assert "/data" in config.folder_paths

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "top_k": 15,
            "use_fuzzy": True,
            "max_edits": 2,
            "search_index_name": "custom_index",
        }

        config = KeywordConfig.from_dict(data)

        assert config.top_k == 15
        assert config.use_fuzzy is True
        assert config.max_edits == 2
        assert config.search_index_name == "custom_index"

    def test_config_weights(self):
        """Test field weight configuration."""
        config = KeywordConfig(
            content_weight=2.0,
            metadata_weight=0.8,
        )

        assert config.content_weight == 2.0
        assert config.metadata_weight == 0.8


class TestKeywordRetriever:
    """Tests for KeywordRetriever."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        chunks_collection = MagicMock()
        chunks_collection.aggregate = MagicMock(return_value=AsyncMock())
        chunks_collection.find = MagicMock(return_value=MagicMock())
        chunks_collection.create_index = AsyncMock()
        db.__getitem__ = MagicMock(return_value=chunks_collection)
        return db

    @pytest.fixture
    def retriever(self, mock_db):
        """Create a retriever with mock database."""
        return KeywordRetriever(db=mock_db)

    def test_create_retriever(self, mock_db):
        """Test creating a keyword retriever."""
        retriever = KeywordRetriever(db=mock_db)

        assert retriever.db == mock_db
        assert retriever.keyword_config.top_k == 10

    def test_create_retriever_with_config(self, mock_db):
        """Test creating retriever with custom config."""
        keyword_config = KeywordConfig(
            top_k=20,
            use_fuzzy=False,
            boost_factor=2.0,
        )
        retriever = KeywordRetriever(
            db=mock_db,
            keyword_config=keyword_config,
        )

        assert retriever.keyword_config.top_k == 20
        assert retriever.keyword_config.use_fuzzy is False
        assert retriever.keyword_config.boost_factor == 2.0

    def test_generate_simple_highlights(self, retriever):
        """Test simple highlight generation."""
        content = "The quick brown fox jumps over the lazy dog."
        query = "fox"

        highlights = retriever._generate_simple_highlights(content, query)

        assert len(highlights) >= 1
        assert any("fox" in h.lower() for h in highlights)

    def test_generate_highlights_multiple_terms(self, retriever):
        """Test highlights with multiple query terms."""
        content = "Python is a programming language. Python is versatile."
        query = "Python programming"

        highlights = retriever._generate_simple_highlights(content, query)

        assert len(highlights) >= 1

    def test_generate_highlights_no_match(self, retriever):
        """Test highlights when no match found."""
        content = "The quick brown fox."
        query = "elephant"

        highlights = retriever._generate_simple_highlights(content, query)

        assert len(highlights) == 0

    def test_generate_highlights_context(self, retriever):
        """Test that highlights include context."""
        content = "This is a very long text with the word python somewhere in the middle of it all."
        query = "python"

        highlights = retriever._generate_simple_highlights(
            content, query, context_chars=20
        )

        assert len(highlights) >= 1
        # Should have context around the match
        assert len(highlights[0]) > len("python")

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self, retriever):
        """Test that empty query returns empty list."""
        result = await retriever.retrieve("", "config-123")
        assert result == []

    @pytest.mark.asyncio
    async def test_retrieve_whitespace_query(self, retriever):
        """Test that whitespace-only query returns empty list."""
        result = await retriever.retrieve("   ", "config-123")
        assert result == []


class TestKeywordRetrieverIntegration:
    """Integration tests for KeywordRetriever with mocked MongoDB."""

    @pytest.fixture
    def mock_db_with_data(self):
        """Create mock database with sample data."""
        db = MagicMock()

        # Sample chunks
        sample_chunks = [
            {
                "_id": "chunk-1",
                "content": "Python is a programming language",
                "document_id": "doc-1",
                "config_id": "config-123",
                "chunk_index": 0,
                "score": 5.0,
            },
            {
                "_id": "chunk-2",
                "content": "Python frameworks like Django are popular",
                "document_id": "doc-1",
                "config_id": "config-123",
                "chunk_index": 1,
                "score": 3.0,
            },
        ]

        # Mock chunks collection
        chunks_collection = MagicMock()

        # Mock aggregate for Atlas Search
        async def mock_aggregate(*args, **kwargs):
            class MockCursor:
                async def to_list(self, length=None):
                    return sample_chunks[:length] if length else sample_chunks

            return MockCursor()

        chunks_collection.aggregate = mock_aggregate

        # Mock find for text index fallback
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=sample_chunks)
        chunks_collection.find = MagicMock(return_value=mock_cursor)

        # Mock create_index
        chunks_collection.create_index = AsyncMock()

        db.__getitem__ = MagicMock(return_value=chunks_collection)
        return db

    def test_source_type_is_keyword(self):
        """Test that keyword retriever sets correct source type."""
        doc = {
            "_id": "chunk-1",
            "content": "Test content",
            "document_id": "doc-1",
            "config_id": "config-123",
            "chunk_index": 0,
        }

        chunk = RetrievedChunk.from_mongo_doc(
            doc=doc,
            score=0.8,
            source_type=SourceType.KEYWORD,
        )

        assert chunk.source_type == SourceType.KEYWORD


class TestBoostFactor:
    """Tests for boost factor application."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        chunks_collection = MagicMock()
        chunks_collection.aggregate = MagicMock(return_value=AsyncMock())
        chunks_collection.create_index = AsyncMock()
        db.__getitem__ = MagicMock(return_value=chunks_collection)
        return db

    def test_boost_factor_default(self, mock_db):
        """Test default boost factor."""
        retriever = KeywordRetriever(db=mock_db)
        assert retriever.keyword_config.boost_factor == 1.0

    def test_boost_factor_custom(self, mock_db):
        """Test custom boost factor."""
        config = KeywordConfig(boost_factor=2.5)
        retriever = KeywordRetriever(db=mock_db, keyword_config=config)
        assert retriever.keyword_config.boost_factor == 2.5


class TestFuzzyMatching:
    """Tests for fuzzy matching configuration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    def test_fuzzy_enabled_default(self, mock_db):
        """Test fuzzy matching is enabled by default."""
        retriever = KeywordRetriever(db=mock_db)
        assert retriever.keyword_config.use_fuzzy is True

    def test_fuzzy_disabled(self, mock_db):
        """Test disabling fuzzy matching."""
        config = KeywordConfig(use_fuzzy=False)
        retriever = KeywordRetriever(db=mock_db, keyword_config=config)
        assert retriever.keyword_config.use_fuzzy is False

    def test_max_edits_default(self, mock_db):
        """Test default max edits for fuzzy matching."""
        retriever = KeywordRetriever(db=mock_db)
        assert retriever.keyword_config.max_edits == 1

    def test_max_edits_custom(self, mock_db):
        """Test custom max edits for fuzzy matching."""
        config = KeywordConfig(max_edits=2)
        retriever = KeywordRetriever(db=mock_db, keyword_config=config)
        assert retriever.keyword_config.max_edits == 2


class TestFilterConfiguration:
    """Tests for filter configuration."""

    def test_folder_paths_filter(self):
        """Test folder paths filter configuration."""
        config = KeywordConfig(folder_paths=["/data/public", "/data/shared"])

        assert len(config.folder_paths) == 2
        assert "/data/public" in config.folder_paths

    def test_access_tags_filter(self):
        """Test access tags filter configuration."""
        config = KeywordConfig(access_tags=["admin", "user"])

        assert len(config.access_tags) == 2
        assert "admin" in config.access_tags

    def test_file_types_filter(self):
        """Test file types filter configuration."""
        config = KeywordConfig(file_types=[".pdf", ".docx"])

        assert len(config.file_types) == 2
        assert ".pdf" in config.file_types

    def test_no_filters_by_default(self):
        """Test that no filters are set by default."""
        config = KeywordConfig()

        assert config.folder_paths is None
        assert config.access_tags is None
        assert config.file_types is None
