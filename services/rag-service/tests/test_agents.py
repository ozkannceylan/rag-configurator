"""Tests for agent module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import (
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentState,
    AgentStep,
    BaseAgent,
    StepType,
)
from app.agents.naive import NaiveRAGAgent
from app.llm.base import LLMResponse, LLMUsage
from app.retrieval.base import RetrievedChunk


class TestStepType:
    """Tests for StepType enum."""

    def test_step_types(self):
        """Test step type values."""
        assert StepType.RETRIEVE.value == "retrieve"
        assert StepType.GENERATE.value == "generate"
        assert StepType.REWRITE.value == "rewrite"
        assert StepType.ROUTE.value == "route"
        assert StepType.ERROR.value == "error"


class TestAgentStep:
    """Tests for AgentStep class."""

    def test_create_step(self):
        """Test creating an agent step."""
        step = AgentStep(
            step_type=StepType.RETRIEVE,
            name="retrieve_chunks",
        )

        assert step.step_type == StepType.RETRIEVE
        assert step.name == "retrieve_chunks"
        assert step.timestamp is not None

    def test_step_with_data(self):
        """Test step with input/output data."""
        step = AgentStep(
            step_type=StepType.GENERATE,
            name="generate_answer",
            input={"query": "test"},
            output={"answer": "response"},
            duration_ms=100.5,
        )

        assert step.input == {"query": "test"}
        assert step.output == {"answer": "response"}
        assert step.duration_ms == 100.5

    def test_step_to_dict(self):
        """Test converting step to dictionary."""
        step = AgentStep(
            step_type=StepType.RETRIEVE,
            name="test_step",
            duration_ms=50.0,
            metadata={"key": "value"},
        )

        data = step.to_dict()

        assert data["step_type"] == "retrieve"
        assert data["name"] == "test_step"
        assert data["duration_ms"] == 50.0
        assert data["metadata"]["key"] == "value"


class TestAgentResponse:
    """Tests for AgentResponse class."""

    def test_create_response(self):
        """Test creating an agent response."""
        response = AgentResponse(
            answer="Test answer",
        )

        assert response.answer == "Test answer"
        assert response.sources == []
        assert response.steps == []

    def test_response_with_sources(self):
        """Test response with sources."""
        sources = [
            RetrievedChunk(
                content="Source content",
                score=0.9,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
            )
        ]
        response = AgentResponse(
            answer="Answer",
            sources=sources,
        )

        assert len(response.sources) == 1
        assert response.source_count == 1

    def test_response_with_steps(self):
        """Test response with steps."""
        steps = [
            AgentStep(step_type=StepType.RETRIEVE, name="retrieve"),
            AgentStep(step_type=StepType.GENERATE, name="generate"),
        ]
        response = AgentResponse(
            answer="Answer",
            steps=steps,
        )

        assert len(response.steps) == 2
        assert response.step_count == 2

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = AgentResponse(
            answer="Test",
            total_duration_ms=150.0,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        data = response.to_dict()

        assert data["answer"] == "Test"
        assert data["total_duration_ms"] == 150.0
        assert data["usage"]["prompt_tokens"] == 100
        assert data["usage"]["total_tokens"] == 150


class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = AgentConfig()

        assert config.top_k == 5
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.streaming is False
        assert config.include_steps is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = AgentConfig(
            top_k=10,
            temperature=0.3,
            max_tokens=4096,
            streaming=True,
            system_prompt_name="technical",
        )

        assert config.top_k == 10
        assert config.temperature == 0.3
        assert config.streaming is True
        assert config.system_prompt_name == "technical"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "top_k": 8,
            "min_score": 0.5,
            "temperature": 0.5,
            "verbose": True,
        }

        config = AgentConfig.from_dict(data)

        assert config.top_k == 8
        assert config.min_score == 0.5
        assert config.temperature == 0.5
        assert config.verbose is True


class TestAgentError:
    """Tests for AgentError class."""

    def test_basic_error(self):
        """Test basic error."""
        error = AgentError("Something went wrong")

        assert "Something went wrong" in str(error)

    def test_error_with_step(self):
        """Test error with step information."""
        error = AgentError(
            message="Retrieval failed",
            step="retrieve",
            details={"query": "test"},
        )

        assert error.step == "retrieve"
        assert error.details["query"] == "test"
        assert "[retrieve]" in str(error)


class TestNaiveRAGAgent:
    """Tests for NaiveRAGAgent."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(
            return_value=[
                RetrievedChunk(
                    content="Test content 1",
                    score=0.9,
                    chunk_id="c1",
                    document_id="d1",
                    config_id="cfg",
                ),
                RetrievedChunk(
                    content="Test content 2",
                    score=0.8,
                    chunk_id="c2",
                    document_id="d1",
                    config_id="cfg",
                ),
            ]
        )
        return retriever

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="This is the generated answer.",
                model="gpt-4o-mini",
                usage=LLMUsage(
                    prompt_tokens=100, completion_tokens=50, total_tokens=150
                ),
            )
        )

        async def mock_stream(*args, **kwargs):
            for chunk in ["This ", "is ", "streaming ", "response."]:
                yield chunk

        llm.stream = mock_stream
        return llm

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock prompt manager."""
        manager = MagicMock()
        manager.get_system_prompt = MagicMock(return_value="You are helpful.")
        manager.get_rag_prompt = MagicMock(
            return_value="Context: {context}\nQuery: {query}"
        )
        manager.format_context = MagicMock(return_value="[1] Content 1\n[2] Content 2")
        manager.format_history = MagicMock(return_value="")
        return manager

    @pytest.fixture
    def agent(self, mock_retriever, mock_llm, mock_prompt_manager):
        """Create a naive RAG agent."""
        return NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
        )

    def test_create_agent(self, mock_retriever, mock_llm):
        """Test creating a naive RAG agent."""
        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
        )

        assert agent.name == "naive_rag"
        assert agent.retriever == mock_retriever
        assert agent.llm == mock_llm

    def test_create_agent_with_config(self, mock_retriever, mock_llm):
        """Test creating agent with custom config."""
        config = AgentConfig(top_k=10, temperature=0.5)
        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            config=config,
        )

        assert agent.config.top_k == 10
        assert agent.config.temperature == 0.5

    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_retriever, mock_llm):
        """Test basic agent run."""
        response = await agent.run(
            query="What is Python?",
            config_id="test-config",
        )

        assert isinstance(response, AgentResponse)
        assert response.answer == "This is the generated answer."
        assert len(response.sources) == 2
        mock_retriever.retrieve.assert_called_once()
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_history(self, agent, mock_retriever, mock_llm):
        """Test agent run with conversation history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        response = await agent.run(
            query="Follow-up question",
            config_id="test-config",
            conversation_history=history,
        )

        assert isinstance(response, AgentResponse)
        assert response.answer is not None

    @pytest.mark.asyncio
    async def test_run_includes_steps(self, agent):
        """Test that run includes execution steps."""
        response = await agent.run(
            query="Test query",
            config_id="test-config",
        )

        # Should have retrieve and generate steps
        assert len(response.steps) >= 2
        step_types = [s.step_type for s in response.steps]
        assert StepType.RETRIEVE in step_types
        assert StepType.GENERATE in step_types

    @pytest.mark.asyncio
    async def test_run_without_steps(
        self, mock_retriever, mock_llm, mock_prompt_manager
    ):
        """Test run without step tracking."""
        config = AgentConfig(include_steps=False)
        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        assert len(response.steps) == 0

    @pytest.mark.asyncio
    async def test_run_tracks_duration(self, agent):
        """Test that run tracks total duration."""
        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        assert response.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_tracks_tokens(self, agent):
        """Test that run tracks token usage."""
        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        assert response.prompt_tokens == 100
        assert response.completion_tokens == 50
        assert response.total_tokens == 150

    @pytest.mark.asyncio
    async def test_run_with_min_score_filter(
        self, mock_retriever, mock_llm, mock_prompt_manager
    ):
        """Test run with minimum score filtering."""
        config = AgentConfig(min_score=0.85)
        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        # Only one chunk has score >= 0.85
        assert len(response.sources) == 1
        assert response.sources[0].score >= 0.85

    @pytest.mark.asyncio
    async def test_run_with_sources(self, agent):
        """Test run_with_sources convenience method."""
        answer, sources = await agent.run_with_sources(
            query="Test",
            config_id="cfg",
        )

        assert isinstance(answer, str)
        assert isinstance(sources, list)
        assert len(sources) == 2

    @pytest.mark.asyncio
    async def test_stream(self, agent):
        """Test streaming response."""
        chunks = []
        async for chunk in agent.stream(
            query="Test",
            config_id="cfg",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "streaming" in full_response

    @pytest.mark.asyncio
    async def test_retrieval_error_handling(self, mock_llm, mock_prompt_manager):
        """Test handling of retrieval errors."""
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(side_effect=Exception("DB error"))

        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        # Should still return a response with error step
        assert response is not None
        error_steps = [s for s in response.steps if s.step_type == StepType.ERROR]
        assert len(error_steps) > 0

    @pytest.mark.asyncio
    async def test_generation_error_handling(self, mock_retriever, mock_prompt_manager):
        """Test handling of generation errors."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))

        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        # Should return a fallback response
        assert response is not None
        assert (
            "error" in response.answer.lower() or "apologize" in response.answer.lower()
        )

    @pytest.mark.asyncio
    async def test_close(self, agent, mock_retriever, mock_llm):
        """Test closing agent resources."""
        mock_retriever.close = AsyncMock()
        mock_llm.close = AsyncMock()

        await agent.close()

        mock_retriever.close.assert_called_once()
        mock_llm.close.assert_called_once()


class TestAgentState:
    """Tests for AgentState TypedDict."""

    def test_create_state(self):
        """Test creating agent state."""
        state: AgentState = {
            "query": "Test query",
            "config_id": "cfg-123",
            "retrieved_chunks": [],
            "context": "",
            "answer": "",
            "steps": [],
        }

        assert state["query"] == "Test query"
        assert state["config_id"] == "cfg-123"

    def test_state_with_chunks(self):
        """Test state with retrieved chunks."""
        chunks = [
            RetrievedChunk(
                content="Test",
                score=0.9,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
            )
        ]
        state: AgentState = {
            "query": "Test",
            "config_id": "cfg",
            "retrieved_chunks": chunks,
        }

        assert len(state["retrieved_chunks"]) == 1


class TestBaseAgent:
    """Tests for BaseAgent abstract class."""

    def test_cannot_instantiate_base(self):
        """Test that BaseAgent cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAgent()

    def test_create_step_helper(self):
        """Test _create_step helper method."""

        # Create a concrete implementation for testing
        class TestAgent(BaseAgent):
            async def run(self, *args, **kwargs):
                pass

            async def stream(self, *args, **kwargs):
                yield ""

        agent = TestAgent()
        step = agent._create_step(
            step_type=StepType.RETRIEVE,
            name="test_step",
            input_data={"key": "value"},
            duration_ms=50.0,
        )

        assert step.step_type == StepType.RETRIEVE
        assert step.name == "test_step"
        assert step.input == {"key": "value"}
        assert step.duration_ms == 50.0

    def test_format_sources_helper(self):
        """Test _format_sources helper method."""

        class TestAgent(BaseAgent):
            async def run(self, *args, **kwargs):
                pass

            async def stream(self, *args, **kwargs):
                yield ""

        agent = TestAgent()
        chunks = [
            RetrievedChunk(
                content="Low score",
                score=0.5,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
            ),
            RetrievedChunk(
                content="High score",
                score=0.9,
                chunk_id="c2",
                document_id="d1",
                config_id="cfg",
            ),
        ]

        formatted = agent._format_sources(chunks, max_sources=1)

        # Should return only top scoring chunk
        assert len(formatted) == 1
        assert formatted[0].score == 0.9


class TestNaiveRAGAgentSimpleFlow:
    """Tests for simple flow (without LangGraph)."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(
            return_value=[
                RetrievedChunk(
                    content="Content",
                    score=0.9,
                    chunk_id="c1",
                    document_id="d1",
                    config_id="cfg",
                ),
            ]
        )
        return retriever

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="Answer",
                model="test-model",
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        )
        return llm

    @pytest.mark.asyncio
    async def test_simple_flow_works(self, mock_retriever, mock_llm):
        """Test that simple flow works without LangGraph."""
        agent = NaiveRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
        )
        # Force simple flow
        agent._use_langgraph = False

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        assert response.answer == "Answer"
        assert len(response.sources) == 1
