"""Tests for GraphRAG agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base import AgentConfig, AgentResponse, AgentStep, StepType
from app.agents.graph_rag import GraphRAGAgent, GraphRAGConfig
from app.llm.base import LLMResponse, LLMUsage, Message
from app.retrieval.base import RetrievedChunk, SourceType


@pytest.fixture
def mock_retriever():
    """Create a mock retriever."""
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock(
        return_value=[
            RetrievedChunk(
                content="Paris is the capital of France.",
                score=0.95,
                chunk_id="chunk-1",
                document_id="doc-1",
                config_id="config-123",
                source_type=SourceType.VECTOR,
                file_name="france.txt",
            ),
        ]
    )
    return retriever


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = AsyncMock()
    llm.generate = AsyncMock(
        return_value=LLMResponse(
            content="Paris is the capital of France.",
            model="gpt-4o-mini",
            usage=LLMUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
        )
    )

    async def mock_stream(*args, **kwargs):
        for word in ["Paris", " is", " the", " capital"]:
            yield word

    llm.stream = mock_stream
    return llm


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database with community summaries."""
    db = MagicMock()
    collection = MagicMock()

    # Mock cursor that acts as an async iterator
    summaries = [
        {
            "community_id": "community-0",
            "summary": "France is a European country with Paris as its capital.",
            "entities": ["France", "Paris", "Europe"],
            "level": 0,
        },
        {
            "community_id": "community-1",
            "summary": "European countries share cultural and economic ties.",
            "entities": ["Europe", "EU", "Economy"],
            "level": 0,
        },
    ]

    class AsyncCursorMock:
        def __init__(self, docs):
            self._docs = docs
            self._index = 0

        def sort(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._index >= len(self._docs):
                raise StopAsyncIteration
            doc = self._docs[self._index]
            self._index += 1
            return doc

    collection.find = MagicMock(return_value=AsyncCursorMock(summaries))
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def graph_rag_agent(mock_retriever, mock_llm, mock_db):
    """Create a GraphRAG agent instance."""
    config = GraphRAGConfig(max_community_summaries=5)
    return GraphRAGAgent(
        retriever=mock_retriever,
        llm=mock_llm,
        config=config,
        db=mock_db,
    )


async def test_classify_query_global(graph_rag_agent, mock_llm):
    """Test that broad queries are classified as global."""
    mock_llm.generate = AsyncMock(
        return_value=LLMResponse(content="global", model="gpt-4o-mini")
    )
    result = await graph_rag_agent._classify_query(
        "What are the main themes across all documents?"
    )
    assert result == "global"


async def test_classify_query_local(graph_rag_agent, mock_llm):
    """Test that specific queries are classified as local."""
    mock_llm.generate = AsyncMock(
        return_value=LLMResponse(content="local", model="gpt-4o-mini")
    )
    result = await graph_rag_agent._classify_query("What is the capital of France?")
    assert result == "local"


async def test_classify_query_default_to_local(graph_rag_agent, mock_llm):
    """Test that ambiguous classification defaults to local."""
    mock_llm.generate = AsyncMock(
        return_value=LLMResponse(content="unclear", model="gpt-4o-mini")
    )
    result = await graph_rag_agent._classify_query("Tell me about X")
    assert result == "local"


async def test_run_global_query(graph_rag_agent, mock_llm):
    """Test GraphRAG with a global (community summary) query."""
    # First call: classify as global. Subsequent calls: generate answer.
    call_count = 0

    async def mock_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(content="global", model="gpt-4o-mini")
        return LLMResponse(
            content="France is a key European country.",
            model="gpt-4o-mini",
            usage=LLMUsage(prompt_tokens=200, completion_tokens=30, total_tokens=230),
        )

    mock_llm.generate = AsyncMock(side_effect=mock_generate)

    response = await graph_rag_agent.run(
        query="What are the main themes?",
        config_id="config-123",
    )

    assert isinstance(response, AgentResponse)
    assert response.answer == "France is a key European country."
    assert response.metadata.get("query_type") == "global"


async def test_run_local_query(graph_rag_agent, mock_llm, mock_retriever):
    """Test GraphRAG with a local (vector retrieval) query."""
    call_count = 0

    async def mock_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(content="local", model="gpt-4o-mini")
        return LLMResponse(
            content="Paris is the capital of France.",
            model="gpt-4o-mini",
            usage=LLMUsage(prompt_tokens=150, completion_tokens=15, total_tokens=165),
        )

    mock_llm.generate = AsyncMock(side_effect=mock_generate)

    response = await graph_rag_agent.run(
        query="What is the capital of France?",
        config_id="config-123",
    )

    assert isinstance(response, AgentResponse)
    assert "Paris" in response.answer
    assert response.metadata.get("query_type") == "local"
    assert len(response.sources) > 0
    mock_retriever.retrieve.assert_called_once()


async def test_run_includes_steps(graph_rag_agent, mock_llm):
    """Test that steps are included when include_steps is True."""
    call_count = 0

    async def mock_generate(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(content="local", model="gpt-4o-mini")
        return LLMResponse(content="answer", model="gpt-4o-mini")

    mock_llm.generate = AsyncMock(side_effect=mock_generate)

    response = await graph_rag_agent.run(
        query="test query",
        config_id="config-123",
    )

    assert len(response.steps) >= 2  # classify + retrieve + generate
    step_names = [s.name for s in response.steps]
    assert "classify_query" in step_names


async def test_graphrag_config_from_dict():
    """Test GraphRAGConfig.from_dict."""
    config = GraphRAGConfig.from_dict({
        "top_k": 10,
        "temperature": 0.5,
        "max_community_summaries": 20,
    })
    assert config.top_k == 10
    assert config.temperature == 0.5
    assert config.max_community_summaries == 20


async def test_no_community_summaries(mock_retriever, mock_llm):
    """Test global query when no community summaries exist."""
    # DB with empty summaries
    db = MagicMock()
    collection = MagicMock()

    class EmptyCursor:
        def sort(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    collection.find = MagicMock(return_value=EmptyCursor())
    db.__getitem__ = MagicMock(return_value=collection)

    agent = GraphRAGAgent(
        retriever=mock_retriever,
        llm=mock_llm,
        config=GraphRAGConfig(),
        db=db,
    )

    mock_llm.generate = AsyncMock(
        return_value=LLMResponse(content="global", model="gpt-4o-mini")
    )

    response = await agent.run(query="What are the main themes?", config_id="cfg-1")
    assert "no community summaries" in response.answer.lower() or "indexing" in response.answer.lower()


async def test_agent_factory_creates_graph_rag():
    """Test that the factory can create a GraphRAG agent."""
    from app.agents.factory import create_agent

    retriever = AsyncMock()
    llm = AsyncMock()

    agent = create_agent(
        agent_type="graph_rag",
        retriever=retriever,
        llm=llm,
    )

    assert isinstance(agent, GraphRAGAgent)
    assert agent.name == "graph_rag"
