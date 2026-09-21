"""Tests for hybrid retrieval and factory modules."""

from unittest.mock import MagicMock

import pytest

from app.retrieval.base import RetrievedChunk
from app.retrieval.factory import (
    RetrievalMethod,
    create_retrieval_config,
    get_retriever,
    get_retriever_from_config,
)
from app.retrieval.hybrid import (
    FusionMethod,
    HybridConfig,
    HybridRetrievalResult,
    HybridRetriever,
    reciprocal_rank_fusion,
)


class TestFusionMethod:
    """Tests for FusionMethod enum."""

    def test_fusion_methods(self):
        """Test fusion method values."""
        assert FusionMethod.RRF.value == "rrf"
        assert FusionMethod.LINEAR.value == "linear"
        assert FusionMethod.MAX.value == "max"
        assert FusionMethod.SUM.value == "sum"


class TestHybridConfig:
    """Tests for HybridConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = HybridConfig()

        assert config.use_vector is True
        assert config.use_keyword is True
        assert config.use_graph is False
        assert config.fusion_method == FusionMethod.RRF
        assert config.rrf_k == 60

    def test_custom_config(self):
        """Test custom configuration."""
        config = HybridConfig(
            use_vector=True,
            use_keyword=True,
            use_graph=True,
            fusion_method=FusionMethod.LINEAR,
            vector_weight=0.6,
            keyword_weight=0.3,
            graph_weight=0.1,
        )

        assert config.use_graph is True
        assert config.fusion_method == FusionMethod.LINEAR
        assert config.vector_weight == 0.6

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "use_vector": True,
            "use_keyword": False,
            "use_graph": True,
            "fusion_method": "max",
            "top_k": 15,
        }

        config = HybridConfig.from_dict(data)

        assert config.use_vector is True
        assert config.use_keyword is False
        assert config.use_graph is True
        assert config.fusion_method == FusionMethod.MAX
        assert config.top_k == 15

    def test_weights_default(self):
        """Test default retriever weights."""
        config = HybridConfig()

        assert config.vector_weight == 0.5
        assert config.keyword_weight == 0.3
        assert config.graph_weight == 0.2


class TestReciprocalRankFusion:
    """Tests for RRF function."""

    def test_rrf_single_ranking(self):
        """Test RRF with single ranking."""
        rankings = [["doc1", "doc2", "doc3"]]
        scores = reciprocal_rank_fusion(rankings, k=60)

        assert "doc1" in scores
        assert "doc2" in scores
        assert "doc3" in scores
        assert scores["doc1"] > scores["doc2"] > scores["doc3"]

    def test_rrf_multiple_rankings(self):
        """Test RRF with multiple rankings."""
        rankings = [
            ["doc1", "doc2", "doc3"],
            ["doc2", "doc1", "doc4"],
        ]
        scores = reciprocal_rank_fusion(rankings, k=60)

        # doc1 and doc2 should have higher scores (appear in both)
        assert scores["doc1"] > scores["doc3"]
        assert scores["doc2"] > scores["doc4"]

    def test_rrf_empty_rankings(self):
        """Test RRF with empty rankings."""
        rankings: list = []
        scores = reciprocal_rank_fusion(rankings)
        assert scores == {}

    def test_rrf_k_parameter(self):
        """Test that k parameter affects scores."""
        rankings = [["doc1", "doc2"]]

        scores_k60 = reciprocal_rank_fusion(rankings, k=60)
        scores_k1 = reciprocal_rank_fusion(rankings, k=1)

        # Higher k = lower scores overall
        assert scores_k1["doc1"] > scores_k60["doc1"]

    def test_rrf_overlap_boost(self):
        """Test that documents appearing in multiple rankings get boosted."""
        rankings = [
            ["doc1", "doc2"],
            ["doc1", "doc3"],
            ["doc1", "doc4"],
        ]
        scores = reciprocal_rank_fusion(rankings, k=60)

        # doc1 appears first in all rankings
        assert scores["doc1"] > scores["doc2"]
        assert scores["doc1"] > scores["doc3"]
        assert scores["doc1"] > scores["doc4"]


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def retriever(self, mock_db):
        """Create a hybrid retriever."""
        return HybridRetriever(db=mock_db)

    def test_create_retriever(self, mock_db):
        """Test creating a hybrid retriever."""
        retriever = HybridRetriever(db=mock_db)

        assert retriever.db == mock_db
        assert retriever.hybrid_config.use_vector is True
        assert retriever.hybrid_config.use_keyword is True

    def test_create_retriever_with_config(self, mock_db):
        """Test creating retriever with custom config."""
        config = HybridConfig(
            use_vector=True,
            use_keyword=False,
            use_graph=True,
            fusion_method=FusionMethod.LINEAR,
        )
        retriever = HybridRetriever(db=mock_db, hybrid_config=config)

        assert retriever.hybrid_config.use_keyword is False
        assert retriever.hybrid_config.use_graph is True

    def test_rrf_fusion(self, retriever):
        """Test RRF fusion method."""
        source_results = {
            "vector": [
                RetrievedChunk(
                    content="A",
                    score=0.9,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
                RetrievedChunk(
                    content="B",
                    score=0.8,
                    chunk_id="2",
                    document_id="d1",
                    config_id="c",
                ),
            ],
            "keyword": [
                RetrievedChunk(
                    content="B",
                    score=0.95,
                    chunk_id="2",
                    document_id="d1",
                    config_id="c",
                ),
                RetrievedChunk(
                    content="C",
                    score=0.7,
                    chunk_id="3",
                    document_id="d1",
                    config_id="c",
                ),
            ],
        }

        fused_chunks, scores = retriever._rrf_fusion(source_results)

        # Chunk 2 should rank higher (appears in both)
        assert len(fused_chunks) == 3
        assert scores["2"] > scores["1"]
        assert scores["2"] > scores["3"]

    def test_linear_fusion(self, mock_db):
        """Test linear fusion method."""
        config = HybridConfig(
            fusion_method=FusionMethod.LINEAR,
            vector_weight=0.7,
            keyword_weight=0.3,
        )
        retriever = HybridRetriever(db=mock_db, hybrid_config=config)

        source_results = {
            "vector": [
                RetrievedChunk(
                    content="A",
                    score=1.0,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
            "keyword": [
                RetrievedChunk(
                    content="A",
                    score=0.5,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
        }

        fused_chunks, scores = retriever._linear_fusion(source_results)

        # Score should be weighted combination
        assert len(fused_chunks) == 1
        # 0.7 * 1.0 + 0.3 * 1.0 (normalized) = 1.0
        assert scores["1"] > 0

    def test_max_fusion(self, mock_db):
        """Test max fusion method."""
        config = HybridConfig(fusion_method=FusionMethod.MAX)
        retriever = HybridRetriever(db=mock_db, hybrid_config=config)

        source_results = {
            "vector": [
                RetrievedChunk(
                    content="A",
                    score=0.7,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
            "keyword": [
                RetrievedChunk(
                    content="A",
                    score=0.9,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
        }

        fused_chunks, scores = retriever._max_fusion(source_results)

        assert scores["1"] == 0.9  # Max of 0.7 and 0.9

    def test_sum_fusion(self, mock_db):
        """Test sum fusion method."""
        config = HybridConfig(fusion_method=FusionMethod.SUM)
        retriever = HybridRetriever(db=mock_db, hybrid_config=config)

        source_results = {
            "vector": [
                RetrievedChunk(
                    content="A",
                    score=0.5,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
            "keyword": [
                RetrievedChunk(
                    content="A",
                    score=0.4,
                    chunk_id="1",
                    document_id="d1",
                    config_id="c",
                ),
            ],
        }

        fused_chunks, scores = retriever._sum_fusion(source_results)

        assert scores["1"] == 0.9  # Sum of 0.5 and 0.4


class TestRetrievalMethod:
    """Tests for RetrievalMethod enum."""

    def test_retrieval_methods(self):
        """Test retrieval method values."""
        assert RetrievalMethod.NAIVE.value == "naive"
        assert RetrievalMethod.VECTOR.value == "vector"
        assert RetrievalMethod.KEYWORD.value == "keyword"
        assert RetrievalMethod.GRAPH.value == "graph"
        assert RetrievalMethod.HYBRID.value == "hybrid"
        assert RetrievalMethod.ADVANCED.value == "advanced"


class TestGetRetriever:
    """Tests for get_retriever factory function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    def test_get_naive_retriever(self, mock_db):
        """Test getting naive (vector) retriever."""
        from app.retrieval.vector import VectorRetriever

        retriever = get_retriever(RetrievalMethod.NAIVE, mock_db)
        assert isinstance(retriever, VectorRetriever)

    def test_get_vector_retriever(self, mock_db):
        """Test getting vector retriever."""
        from app.retrieval.vector import VectorRetriever

        retriever = get_retriever(RetrievalMethod.VECTOR, mock_db)
        assert isinstance(retriever, VectorRetriever)

    def test_get_keyword_retriever(self, mock_db):
        """Test getting keyword retriever."""
        from app.retrieval.keyword import KeywordRetriever

        retriever = get_retriever(RetrievalMethod.KEYWORD, mock_db)
        assert isinstance(retriever, KeywordRetriever)

    def test_get_graph_retriever(self, mock_db):
        """Test getting graph retriever."""
        from app.retrieval.graph import GraphRetriever

        retriever = get_retriever(RetrievalMethod.GRAPH, mock_db)
        assert isinstance(retriever, GraphRetriever)

    def test_get_hybrid_retriever(self, mock_db):
        """Test getting hybrid retriever."""
        from app.retrieval.hybrid import HybridRetriever

        retriever = get_retriever(RetrievalMethod.HYBRID, mock_db)
        assert isinstance(retriever, HybridRetriever)

    def test_get_advanced_retriever(self, mock_db):
        """Test getting advanced retriever."""
        from app.retrieval.hybrid import HybridRetriever

        retriever = get_retriever(RetrievalMethod.ADVANCED, mock_db)
        assert isinstance(retriever, HybridRetriever)

    def test_unknown_method_raises(self, mock_db):
        """Test that unknown method raises error."""
        with pytest.raises(ValueError):
            get_retriever("unknown_method", mock_db)


class TestGetRetrieverFromConfig:
    """Tests for get_retriever_from_config function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    def test_from_naive_config(self, mock_db):
        """Test creating retriever from naive config."""
        from app.retrieval.vector import VectorRetriever

        config = {"retrieval": {"method": "naive"}}
        retriever = get_retriever_from_config(mock_db, config)
        assert isinstance(retriever, VectorRetriever)

    def test_from_hybrid_config(self, mock_db):
        """Test creating retriever from hybrid config."""
        from app.retrieval.hybrid import HybridRetriever

        config = {
            "retrieval": {
                "method": "hybrid",
                "top_k": 10,
                "hybrid": {
                    "use_vector": True,
                    "use_keyword": True,
                    "fusion_method": "rrf",
                },
            }
        }
        retriever = get_retriever_from_config(mock_db, config)
        assert isinstance(retriever, HybridRetriever)

    def test_from_empty_config(self, mock_db):
        """Test creating retriever from empty config defaults to naive."""
        from app.retrieval.vector import VectorRetriever

        config: dict = {}
        retriever = get_retriever_from_config(mock_db, config)
        assert isinstance(retriever, VectorRetriever)


class TestCreateRetrievalConfig:
    """Tests for create_retrieval_config helper."""

    def test_default_config(self):
        """Test creating config with defaults."""
        config = create_retrieval_config()

        assert config.top_k == 5
        assert config.min_score == 0.0
        assert config.embedding_provider == "openai"

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = create_retrieval_config(
            top_k=10,
            min_score=0.5,
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
            folder_paths=["/data"],
        )

        assert config.top_k == 10
        assert config.min_score == 0.5
        assert config.embedding_provider == "ollama"
        assert "/data" in config.folder_paths


class TestHybridRetrievalResult:
    """Tests for HybridRetrievalResult."""

    def test_create_result(self):
        """Test creating hybrid retrieval result."""
        chunks = [
            RetrievedChunk(
                content="Test",
                score=0.9,
                chunk_id="1",
                document_id="d1",
                config_id="c",
            )
        ]

        result = HybridRetrievalResult(
            chunks=chunks,
            source_counts={"vector": 5, "keyword": 3},
            retrieval_time_ms=50.0,
        )

        assert len(result.chunks) == 1
        assert result.source_counts["vector"] == 5
        assert result.retrieval_time_ms == 50.0

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = HybridRetrievalResult(
            chunks=[],
            source_counts={"vector": 2},
            retrieval_time_ms=25.0,
        )

        data = result.to_dict()

        assert data["chunks"] == []
        assert data["source_counts"]["vector"] == 2
        assert data["total_results"] == 0
