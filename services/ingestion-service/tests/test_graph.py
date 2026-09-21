"""Tests for graph extraction, storage, community detection, and summarization."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.graph.builder import GraphBuildConfig, GraphBuilder, GraphBuildResult
from app.graph.community import CommunityDetector
from app.graph.extractor import (
    EntityExtractor,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionConfig,
    ExtractionResult,
)
from app.graph.models import Community, CommunitySummary, Entity, Relation
from app.graph.summarizer import CommunitySummarizer
from app.storage.graph_store import GraphEdge, GraphNode, GraphStore


class TestExtractionConfig:
    """Tests for ExtractionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExtractionConfig()

        assert config.llm_provider == "ollama"
        assert config.llm_model == "llama3.2"
        assert config.auto_extract is True
        assert config.max_entities_per_chunk == 50
        assert config.min_confidence == 0.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExtractionConfig(
            llm_provider="openai",
            llm_model="gpt-4",
            entity_types=["person", "organization"],
            relation_types=["works_for", "located_in"],
            auto_extract=False,
        )

        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert "person" in config.entity_types
        assert config.auto_extract is False


class TestExtractedEntity:
    """Tests for ExtractedEntity."""

    def test_create_entity(self):
        """Test creating an entity."""
        entity = ExtractedEntity(
            name="John Doe",
            entity_type="person",
            confidence=0.95,
        )

        assert entity.name == "John Doe"
        assert entity.entity_type == "person"
        assert entity.confidence == 0.95

    def test_entity_to_dict(self):
        """Test converting entity to dict."""
        entity = ExtractedEntity(
            name="Acme Corp",
            entity_type="organization",
            properties={"industry": "technology"},
        )

        data = entity.to_dict()

        assert data["name"] == "Acme Corp"
        assert data["entity_type"] == "organization"
        assert data["properties"]["industry"] == "technology"


class TestExtractedRelation:
    """Tests for ExtractedRelation."""

    def test_create_relation(self):
        """Test creating a relation."""
        relation = ExtractedRelation(
            source_entity="John Doe",
            target_entity="Acme Corp",
            relation_type="works_for",
            confidence=0.9,
        )

        assert relation.source_entity == "John Doe"
        assert relation.target_entity == "Acme Corp"
        assert relation.relation_type == "works_for"

    def test_relation_to_dict(self):
        """Test converting relation to dict."""
        relation = ExtractedRelation(
            source_entity="London",
            target_entity="UK",
            relation_type="located_in",
        )

        data = relation.to_dict()

        assert data["source_entity"] == "London"
        assert data["target_entity"] == "UK"
        assert data["relation_type"] == "located_in"


class TestEntityExtractor:
    """Tests for EntityExtractor."""

    def test_create_extractor(self):
        """Test creating an extractor."""
        config = ExtractionConfig(llm_model="llama3.2")
        extractor = EntityExtractor(config)

        assert extractor.config.llm_model == "llama3.2"

    def test_build_prompt_auto_extract(self):
        """Test building prompt with auto extract."""
        config = ExtractionConfig(auto_extract=True)
        extractor = EntityExtractor(config)

        prompt = extractor._build_prompt("John works at Acme.")

        assert "John works at Acme." in prompt
        assert "Identify all significant entities" in prompt

    def test_build_prompt_schema_constrained(self):
        """Test building prompt with schema constraints."""
        config = ExtractionConfig(
            auto_extract=False,
            entity_types=["person", "company"],
            relation_types=["works_for"],
        )
        extractor = EntityExtractor(config)

        prompt = extractor._build_prompt("Test text")

        assert "person" in prompt
        assert "company" in prompt
        assert "works_for" in prompt

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        extractor = EntityExtractor()

        response = """
        {
            "entities": [
                {"name": "John Doe", "type": "person", "confidence": 0.9},
                {"name": "Acme Corp", "type": "organization", "confidence": 0.85}
            ],
            "relations": [
                {"source": "John Doe", "target": "Acme Corp", "type": "works_for", "confidence": 0.8}
            ]
        }
        """

        entities, relations = extractor._parse_response(response)

        assert len(entities) == 2
        assert entities[0].name == "John Doe"
        assert entities[1].entity_type == "organization"

        assert len(relations) == 1
        assert relations[0].relation_type == "works_for"

    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON response."""
        extractor = EntityExtractor()

        entities, relations = extractor._parse_response("not valid json")

        assert len(entities) == 0
        assert len(relations) == 0

    def test_parse_response_filters_low_confidence(self):
        """Test that low confidence results are filtered."""
        config = ExtractionConfig(min_confidence=0.7)
        extractor = EntityExtractor(config)

        response = """
        {
            "entities": [
                {"name": "High Conf", "type": "person", "confidence": 0.9},
                {"name": "Low Conf", "type": "person", "confidence": 0.3}
            ],
            "relations": []
        }
        """

        entities, relations = extractor._parse_response(response)

        assert len(entities) == 1
        assert entities[0].name == "High Conf"

    def test_parse_response_limits_entities(self):
        """Test that entities are limited per chunk."""
        config = ExtractionConfig(max_entities_per_chunk=2)
        extractor = EntityExtractor(config)

        response = """
        {
            "entities": [
                {"name": "Entity1", "type": "test", "confidence": 0.7},
                {"name": "Entity2", "type": "test", "confidence": 0.9},
                {"name": "Entity3", "type": "test", "confidence": 0.8},
                {"name": "Entity4", "type": "test", "confidence": 0.6}
            ],
            "relations": []
        }
        """

        entities, relations = extractor._parse_response(response)

        assert len(entities) == 2
        # Should keep highest confidence
        assert entities[0].name == "Entity2"
        assert entities[1].name == "Entity3"

    @pytest.mark.asyncio
    async def test_extract_empty_text(self):
        """Test extracting from empty text."""
        extractor = EntityExtractor()

        result = await extractor.extract("")

        assert len(result.entities) == 0
        assert len(result.relations) == 0


class TestGraphNode:
    """Tests for GraphNode model."""

    def test_create_node(self):
        """Test creating a graph node."""
        node = GraphNode(
            config_id="config-123",
            node_type="person",
            name="John Doe",
        )

        assert node.config_id == "config-123"
        assert node.node_type == "person"
        assert node.name == "John Doe"

    def test_node_to_mongo(self):
        """Test converting node to MongoDB document."""
        node = GraphNode(
            config_id="config-123",
            node_type="organization",
            name="Acme Corp",
            properties={"industry": "tech"},
        )

        mongo_doc = node.to_mongo()

        assert mongo_doc["config_id"] == "config-123"
        assert mongo_doc["name"] == "Acme Corp"
        assert mongo_doc["properties"]["industry"] == "tech"

    def test_node_defaults(self):
        """Test node default values."""
        node = GraphNode(
            config_id="config-123",
            node_type="test",
            name="Test Node",
        )

        assert node.embedding == []
        assert node.source_chunks == []
        assert node.mention_count == 1
        assert node.confidence == 1.0


class TestGraphEdge:
    """Tests for GraphEdge model."""

    def test_create_edge(self):
        """Test creating a graph edge."""
        edge = GraphEdge(
            config_id="config-123",
            relation_type="works_for",
            source_node="node-1",
            target_node="node-2",
        )

        assert edge.config_id == "config-123"
        assert edge.relation_type == "works_for"
        assert edge.source_node == "node-1"
        assert edge.target_node == "node-2"

    def test_edge_to_mongo(self):
        """Test converting edge to MongoDB document."""
        edge = GraphEdge(
            config_id="config-123",
            relation_type="located_in",
            source_node="node-1",
            target_node="node-2",
            source_name="London",
            target_name="UK",
        )

        mongo_doc = edge.to_mongo()

        assert mongo_doc["relation_type"] == "located_in"
        assert mongo_doc["source_name"] == "London"
        assert mongo_doc["target_name"] == "UK"

    def test_edge_defaults(self):
        """Test edge default values."""
        edge = GraphEdge(
            config_id="config-123",
            relation_type="test",
            source_node="node-1",
            target_node="node-2",
        )

        assert edge.weight == 1.0
        assert edge.confidence == 1.0
        assert edge.source_chunks == []


class TestGraphStoreHelpers:
    """Tests for GraphStore helper methods."""

    def test_normalize_name(self):
        """Test name normalization."""
        assert GraphStore.normalize_name("John Doe") == "john doe"
        assert GraphStore.normalize_name("  ACME Corp  ") == "acme corp"
        assert GraphStore.normalize_name("Test") == "test"


class TestGraphBuildConfig:
    """Tests for GraphBuildConfig."""

    def test_default_config(self):
        """Test default build configuration."""
        config = GraphBuildConfig()

        assert config.deduplicate_entities is True
        assert config.embed_entities is False
        assert config.merge_threshold == 0.9

    def test_custom_config(self):
        """Test custom build configuration."""
        extraction_config = ExtractionConfig(llm_model="gpt-4")
        config = GraphBuildConfig(
            extraction_config=extraction_config,
            embed_entities=True,
            embedding_provider="openai",
        )

        assert config.extraction_config.llm_model == "gpt-4"
        assert config.embed_entities is True


class TestGraphBuildResult:
    """Tests for GraphBuildResult."""

    def test_default_result(self):
        """Test default build result."""
        result = GraphBuildResult()

        assert result.nodes_created == 0
        assert result.edges_created == 0
        assert result.chunks_processed == 0
        assert result.errors == []

    def test_result_tracking(self):
        """Test tracking results."""
        result = GraphBuildResult()
        result.nodes_created += 5
        result.edges_created += 3
        result.chunks_processed += 10
        result.errors.append({"type": "test", "error": "test error"})

        assert result.nodes_created == 5
        assert result.edges_created == 3
        assert result.chunks_processed == 10
        assert len(result.errors) == 1


class TestGraphBuilder:
    """Tests for GraphBuilder."""

    def test_create_builder(self):
        """Test creating a graph builder."""
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        store = GraphStore(mock_db)
        builder = GraphBuilder(store)

        assert builder.store == store
        assert builder.config is not None

    def test_create_builder_with_config(self):
        """Test creating builder with custom config."""
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        store = GraphStore(mock_db)

        config = GraphBuildConfig(embed_entities=True)
        builder = GraphBuilder(store, config)

        assert builder.config.embed_entities is True

    @pytest.mark.asyncio
    async def test_build_from_text_empty(self):
        """Test building from empty text."""
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=MagicMock())
        store = GraphStore(mock_db)
        builder = GraphBuilder(store)

        result = await builder.build_from_chunks(
            chunks=[{"content": "", "chunk_id": "1"}],
            config_id="config-123",
        )

        assert result.chunks_processed == 0


class TestExtractionResult:
    """Tests for ExtractionResult."""

    def test_default_result(self):
        """Test default extraction result."""
        result = ExtractionResult()

        assert result.entities == []
        assert result.relations == []
        assert result.raw_response == ""
        assert result.tokens_used == 0

    def test_result_with_data(self):
        """Test extraction result with data."""
        entities = [ExtractedEntity(name="Test", entity_type="test")]
        relations = [
            ExtractedRelation(
                source_entity="A", target_entity="B", relation_type="related"
            )
        ]

        result = ExtractionResult(
            entities=entities,
            relations=relations,
            raw_response='{"test": true}',
            tokens_used=100,
        )

        assert len(result.entities) == 1
        assert len(result.relations) == 1
        assert result.tokens_used == 100


# ==================== Community Detection Tests ====================


class TestCommunityModels:
    """Tests for GraphRAG community data models."""

    def test_entity_to_dict(self):
        """Test Entity serialization."""
        e = Entity(
            name="Python",
            type="Technology",
            description="A programming language",
            chunk_ids=["c-1", "c-2"],
            properties={"version": "3.12"},
        )
        d = e.to_dict()
        assert d["name"] == "Python"
        assert d["type"] == "Technology"
        assert len(d["chunk_ids"]) == 2

    def test_entity_from_dict(self):
        """Test Entity deserialization."""
        data = {"name": "Paris", "type": "Location", "description": "Capital"}
        e = Entity.from_dict(data)
        assert e.name == "Paris"
        assert e.chunk_ids == []

    def test_relation_to_dict(self):
        """Test Relation serialization."""
        r = Relation(source="A", target="B", type="REL", description="test")
        d = r.to_dict()
        assert d["source"] == "A"
        assert d["target"] == "B"

    def test_community_roundtrip(self):
        """Test Community to_dict / from_dict roundtrip."""
        c = Community(
            id="comm-0",
            entities=[Entity(name="X", type="T")],
            relations=[Relation(source="X", target="Y", type="R")],
            level=1,
        )
        d = c.to_dict()
        c2 = Community.from_dict(d)
        assert c2.id == "comm-0"
        assert len(c2.entities) == 1
        assert c2.level == 1

    def test_community_summary_to_dict(self):
        """Test CommunitySummary serialization."""
        cs = CommunitySummary(
            community_id="comm-0",
            config_id="cfg-1",
            summary="A summary.",
            entities=["X", "Y"],
        )
        d = cs.to_dict()
        assert d["community_id"] == "comm-0"
        assert d["created_at"] is not None


class TestCommunityDetector:
    """Tests for CommunityDetector."""

    @pytest.fixture
    def sample_entities(self):
        return [
            Entity(name="Python", type="Language", chunk_ids=["c1"]),
            Entity(name="Guido", type="Person", chunk_ids=["c1"]),
            Entity(name="JavaScript", type="Language", chunk_ids=["c2"]),
            Entity(name="Brendan", type="Person", chunk_ids=["c2"]),
            Entity(name="Rust", type="Language", chunk_ids=["c3"]),
        ]

    @pytest.fixture
    def sample_relations(self):
        return [
            Relation(source="Python", target="Guido", type="CREATED_BY"),
            Relation(source="JavaScript", target="Brendan", type="CREATED_BY"),
        ]

    @pytest.mark.asyncio
    async def test_connected_components(self, sample_entities, sample_relations):
        """Test fallback connected-components community detection."""
        detector = CommunityDetector()
        detector._has_leiden = False

        communities = await detector.detect_communities(
            sample_entities, sample_relations
        )
        assert len(communities) > 0

        # Python + Guido in one community
        for c in communities:
            names = {e.name for e in c.entities}
            if "Python" in names:
                assert "Guido" in names
            if "JavaScript" in names:
                assert "Brendan" in names

    @pytest.mark.asyncio
    async def test_empty_entities(self):
        """Test detection with no entities."""
        detector = CommunityDetector()
        assert await detector.detect_communities([], []) == []

    @pytest.mark.asyncio
    async def test_no_relations(self, sample_entities):
        """Test that entities without relations become singleton communities."""
        detector = CommunityDetector()
        detector._has_leiden = False
        communities = await detector.detect_communities(sample_entities, [])
        assert len(communities) == len(sample_entities)

    @pytest.mark.asyncio
    async def test_extract_entities_relations(self):
        """Test entity extraction from chunks using mock LLM."""
        detector = CommunityDetector()

        async def mock_llm(prompt):
            return """{
                "entities": [
                    {"name": "Python", "type": "Language", "description": "A language"}
                ],
                "relations": [
                    {"source": "Python", "target": "Guido", "type": "CREATED_BY"}
                ]
            }"""

        chunks = [{"content": "Python was created by Guido.", "chunk_id": "c-1"}]
        entities, relations = await detector.extract_entities_relations(
            chunks, mock_llm
        )
        assert len(entities) >= 1
        assert any(e.name == "Python" for e in entities)

    @pytest.mark.asyncio
    async def test_extract_handles_llm_error(self):
        """Test graceful handling of LLM errors."""
        detector = CommunityDetector()

        async def fail_llm(prompt):
            raise RuntimeError("unavailable")

        entities, relations = await detector.extract_entities_relations(
            [{"content": "text", "chunk_id": "c1"}], fail_llm
        )
        assert entities == []
        assert relations == []

    def test_parse_extraction_from_markdown(self):
        """Test JSON parsing from markdown code fences."""
        raw = (
            '```json\n{"entities": [{"name": "A", "type": "X"}], "relations": []}\n```'
        )
        result = CommunityDetector._parse_extraction(raw)
        assert len(result["entities"]) == 1


class TestCommunitySummarizer:
    """Tests for CommunitySummarizer."""

    @pytest.mark.asyncio
    async def test_summarize_communities(self):
        """Test community summarization with mock LLM."""
        summarizer = CommunitySummarizer()

        async def mock_llm(prompt):
            return "This community is about programming languages."

        communities = [
            Community(
                id="comm-0",
                entities=[Entity(name="Python", type="Language")],
                relations=[],
            )
        ]
        summaries = await summarizer.summarize_communities(
            communities, mock_llm, "cfg-1"
        )
        assert len(summaries) == 1
        assert summaries[0].config_id == "cfg-1"
        assert "Python" in summaries[0].entities

    @pytest.mark.asyncio
    async def test_skip_empty_communities(self):
        """Test that empty communities are skipped."""
        summarizer = CommunitySummarizer()

        async def mock_llm(prompt):
            return "Summary."

        communities = [Community(id="empty", entities=[], relations=[])]
        summaries = await summarizer.summarize_communities(
            communities, mock_llm, "cfg-1"
        )
        assert len(summaries) == 0

    @pytest.mark.asyncio
    async def test_store_summaries_to_db(self):
        """Test MongoDB persistence."""
        summarizer = CommunitySummarizer()

        async def mock_llm(prompt):
            return "A summary."

        mock_col = MagicMock()
        mock_col.insert_many = AsyncMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_col)

        communities = [
            Community(id="c0", entities=[Entity(name="X", type="T")], relations=[])
        ]
        await summarizer.summarize_communities(
            communities, mock_llm, "cfg-1", db=mock_db
        )
        mock_col.insert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_llm_failure(self):
        """Test graceful LLM failure handling."""
        summarizer = CommunitySummarizer()

        async def fail_llm(prompt):
            raise Exception("LLM down")

        communities = [
            Community(id="c0", entities=[Entity(name="X", type="T")], relations=[])
        ]
        summaries = await summarizer.summarize_communities(
            communities, fail_llm, "cfg-1"
        )
        assert len(summaries) == 0
