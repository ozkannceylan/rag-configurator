"""Tests for graph retrieval module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.retrieval.graph import (
    GraphRetriever,
    GraphConfig,
    GraphContext,
    GraphNode,
    GraphEdge,
    GraphRetrievalResult,
)
from app.retrieval.base import SourceType


class TestGraphNode:
    """Tests for GraphNode."""

    def test_create_node(self):
        """Test creating a graph node."""
        node = GraphNode(
            node_id="node-123",
            name="John Doe",
            node_type="person",
        )

        assert node.node_id == "node-123"
        assert node.name == "John Doe"
        assert node.node_type == "person"
        assert node.score == 0.0
        assert node.depth == 0

    def test_node_with_properties(self):
        """Test node with properties."""
        node = GraphNode(
            node_id="node-123",
            name="Acme Corp",
            node_type="organization",
            properties={"industry": "technology", "size": "large"},
            score=0.95,
            depth=1,
        )

        assert node.properties["industry"] == "technology"
        assert node.score == 0.95
        assert node.depth == 1

    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        node = GraphNode(
            node_id="node-123",
            name="Test Entity",
            node_type="concept",
            score=0.8,
        )

        data = node.to_dict()

        assert data["node_id"] == "node-123"
        assert data["name"] == "Test Entity"
        assert data["node_type"] == "concept"
        assert data["score"] == 0.8


class TestGraphEdge:
    """Tests for GraphEdge."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            edge_id="edge-123",
            source_node="node-1",
            target_node="node-2",
            relation_type="works_for",
        )

        assert edge.edge_id == "edge-123"
        assert edge.source_node == "node-1"
        assert edge.target_node == "node-2"
        assert edge.relation_type == "works_for"

    def test_edge_with_properties(self):
        """Test edge with properties."""
        edge = GraphEdge(
            edge_id="edge-123",
            source_node="node-1",
            target_node="node-2",
            relation_type="located_in",
            properties={"since": "2020"},
            weight=2.5,
        )

        assert edge.properties["since"] == "2020"
        assert edge.weight == 2.5

    def test_edge_to_dict(self):
        """Test converting edge to dictionary."""
        edge = GraphEdge(
            edge_id="edge-123",
            source_node="node-1",
            target_node="node-2",
            relation_type="related_to",
        )

        data = edge.to_dict()

        assert data["edge_id"] == "edge-123"
        assert data["relation_type"] == "related_to"


class TestGraphContext:
    """Tests for GraphContext."""

    def test_create_context(self):
        """Test creating graph context."""
        nodes = [
            GraphNode(node_id="1", name="Entity1", node_type="type1"),
            GraphNode(node_id="2", name="Entity2", node_type="type2"),
        ]
        edges = [
            GraphEdge(
                edge_id="e1",
                source_node="1",
                target_node="2",
                relation_type="related",
            ),
        ]

        context = GraphContext(
            nodes=nodes,
            edges=edges,
            query_entities=["Entity1"],
        )

        assert len(context.nodes) == 2
        assert len(context.edges) == 1
        assert "Entity1" in context.query_entities

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = GraphContext(
            nodes=[GraphNode(node_id="1", name="Test", node_type="test")],
            edges=[],
            query_entities=["Test"],
        )

        data = context.to_dict()

        assert data["node_count"] == 1
        assert data["edge_count"] == 0
        assert "Test" in data["query_entities"]


class TestGraphConfig:
    """Tests for GraphConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = GraphConfig()

        assert config.top_k_nodes == 5
        assert config.min_node_score == 0.5
        assert config.max_depth == 2
        assert config.top_k_chunks == 10
        assert config.include_graph_context is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = GraphConfig(
            top_k_nodes=10,
            min_node_score=0.7,
            max_depth=3,
            max_nodes_per_level=15,
            node_types=["person", "organization"],
            relation_types=["works_for", "knows"],
        )

        assert config.top_k_nodes == 10
        assert config.min_node_score == 0.7
        assert config.max_depth == 3
        assert "person" in config.node_types
        assert "works_for" in config.relation_types

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "top_k_nodes": 8,
            "max_depth": 4,
            "include_graph_context": False,
            "node_types": ["concept"],
        }

        config = GraphConfig.from_dict(data)

        assert config.top_k_nodes == 8
        assert config.max_depth == 4
        assert config.include_graph_context is False
        assert "concept" in config.node_types


class TestGraphRetrievalResult:
    """Tests for GraphRetrievalResult."""

    def test_create_result(self):
        """Test creating retrieval result."""
        from app.retrieval.base import RetrievedChunk

        chunks = [
            RetrievedChunk(
                content="Test content",
                score=0.9,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
                source_type=SourceType.GRAPH,
            )
        ]

        result = GraphRetrievalResult(
            chunks=chunks,
            query_entities=["Entity1"],
            retrieval_time_ms=50.0,
        )

        assert len(result.chunks) == 1
        assert "Entity1" in result.query_entities
        assert result.retrieval_time_ms == 50.0

    def test_result_with_context(self):
        """Test result with graph context."""
        context = GraphContext(
            nodes=[GraphNode(node_id="1", name="Test", node_type="test")],
            edges=[],
            query_entities=["Test"],
        )

        result = GraphRetrievalResult(
            chunks=[],
            graph_context=context,
        )

        assert result.graph_context is not None
        assert len(result.graph_context.nodes) == 1

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = GraphRetrievalResult(
            chunks=[],
            query_entities=["Entity"],
            retrieval_time_ms=25.5,
        )

        data = result.to_dict()

        assert data["chunks"] == []
        assert data["query_entities"] == ["Entity"]
        assert data["retrieval_time_ms"] == 25.5


class TestGraphRetriever:
    """Tests for GraphRetriever."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()

        # Mock collections
        for collection_name in ["graph_nodes", "graph_edges", "chunks", "documents"]:
            collection = MagicMock()
            collection.find = MagicMock(return_value=MagicMock())
            collection.find_one = AsyncMock(return_value=None)
            collection.aggregate = MagicMock(return_value=AsyncMock())
            db.__getitem__ = MagicMock(return_value=collection)

        return db

    @pytest.fixture
    def retriever(self, mock_db):
        """Create a retriever with mock database."""
        return GraphRetriever(db=mock_db)

    def test_create_retriever(self, mock_db):
        """Test creating a graph retriever."""
        retriever = GraphRetriever(db=mock_db)

        assert retriever.db == mock_db
        assert retriever.graph_config.max_depth == 2

    def test_create_retriever_with_config(self, mock_db):
        """Test creating retriever with custom config."""
        config = GraphConfig(max_depth=5, top_k_nodes=10)
        retriever = GraphRetriever(db=mock_db, graph_config=config)

        assert retriever.graph_config.max_depth == 5
        assert retriever.graph_config.top_k_nodes == 10

    def test_cosine_similarity_identical(self, retriever):
        """Test cosine similarity with identical vectors."""
        vec = [1.0, 0.0, 0.0]
        similarity = retriever._cosine_similarity(vec, vec)
        assert similarity == 1.0

    def test_cosine_similarity_orthogonal(self, retriever):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_different_lengths(self, retriever):
        """Test cosine similarity with different length vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_zero_vector(self, retriever):
        """Test cosine similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0


class TestGraphTraversal:
    """Tests for graph traversal logic."""

    def test_node_depth_tracking(self):
        """Test that node depth is tracked correctly."""
        # Starting nodes at depth 0
        node0 = GraphNode(
            node_id="1",
            name="Start",
            node_type="test",
            depth=0,
        )

        # Traversed nodes at depth 1
        node1 = GraphNode(
            node_id="2",
            name="Connected",
            node_type="test",
            depth=1,
        )

        assert node0.depth == 0
        assert node1.depth == 1

    def test_max_nodes_per_level_config(self):
        """Test max nodes per level configuration."""
        config = GraphConfig(max_nodes_per_level=5)
        assert config.max_nodes_per_level == 5

        config_default = GraphConfig()
        assert config_default.max_nodes_per_level == 10


class TestGraphFilters:
    """Tests for graph filter configuration."""

    def test_node_type_filter(self):
        """Test node type filter configuration."""
        config = GraphConfig(node_types=["person", "organization", "location"])
        assert len(config.node_types) == 3
        assert "person" in config.node_types

    def test_relation_type_filter(self):
        """Test relation type filter configuration."""
        config = GraphConfig(
            relation_types=["works_for", "located_in", "knows"]
        )
        assert len(config.relation_types) == 3
        assert "works_for" in config.relation_types

    def test_no_filters_by_default(self):
        """Test that no filters are set by default."""
        config = GraphConfig()
        assert config.node_types is None
        assert config.relation_types is None


class TestSourceTypeGraph:
    """Tests for graph source type."""

    def test_source_type_value(self):
        """Test graph source type value."""
        assert SourceType.GRAPH.value == "graph"

    def test_chunk_with_graph_source(self):
        """Test creating chunk with graph source type."""
        from app.retrieval.base import RetrievedChunk

        chunk = RetrievedChunk(
            content="Graph content",
            score=0.85,
            chunk_id="c1",
            document_id="d1",
            config_id="cfg",
            source_type=SourceType.GRAPH,
        )

        assert chunk.source_type == SourceType.GRAPH
        assert chunk.to_dict()["source_type"] == "graph"
