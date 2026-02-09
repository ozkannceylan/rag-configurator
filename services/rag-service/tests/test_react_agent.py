"""Tests for ReAct agent module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.react import (
    ReActAgent,
    ReActConfig,
    ReActState,
    Tool,
    ToolType,
    Thought,
    Action,
    Observation,
    REACT_SYSTEM_PROMPT,
)
from app.agents.base import AgentResponse, StepType
from app.retrieval.base import RetrievedChunk
from app.llm.base import Message, LLMResponse, LLMUsage


class TestToolType:
    """Tests for ToolType enum."""

    def test_tool_types(self):
        """Test tool type values."""
        assert ToolType.SEARCH.value == "search"
        assert ToolType.RETRIEVE.value == "retrieve"
        assert ToolType.CALCULATE.value == "calculate"
        assert ToolType.LOOKUP.value == "lookup"
        assert ToolType.NONE.value == "none"


class TestTool:
    """Tests for Tool class."""

    def test_create_tool(self):
        """Test creating a tool."""
        async def handler(input, config_id, state):
            return "result"

        tool = Tool(
            name="test_tool",
            description="A test tool",
            tool_type=ToolType.SEARCH,
            handler=handler,
            parameters={"query": "The search query"},
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.tool_type == ToolType.SEARCH

    def test_tool_to_dict(self):
        """Test converting tool to dictionary."""
        tool = Tool(
            name="search",
            description="Search for information",
            tool_type=ToolType.SEARCH,
            handler=lambda x, y, z: "result",
            parameters={"query": "Search query"},
        )

        data = tool.to_dict()

        assert data["name"] == "search"
        assert data["description"] == "Search for information"
        assert "query" in data["parameters"]


class TestThought:
    """Tests for Thought class."""

    def test_create_thought(self):
        """Test creating a thought."""
        thought = Thought(
            content="I need to search for information",
            iteration=0,
        )

        assert thought.content == "I need to search for information"
        assert thought.iteration == 0
        assert thought.timestamp > 0


class TestAction:
    """Tests for Action class."""

    def test_create_action(self):
        """Test creating an action."""
        action = Action(
            tool="search",
            input="Python programming",
            iteration=1,
        )

        assert action.tool == "search"
        assert action.input == "Python programming"
        assert action.iteration == 1


class TestObservation:
    """Tests for Observation class."""

    def test_create_observation(self):
        """Test creating an observation."""
        observation = Observation(
            content="Python is a programming language",
            tool="search",
            iteration=1,
            success=True,
        )

        assert observation.content == "Python is a programming language"
        assert observation.tool == "search"
        assert observation.success is True

    def test_failed_observation(self):
        """Test failed observation."""
        observation = Observation(
            content="Error: API failed",
            tool="search",
            iteration=0,
            success=False,
        )

        assert observation.success is False


class TestReActConfig:
    """Tests for ReActConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = ReActConfig()

        assert config.max_iterations == 5
        assert config.thought_temperature == 0.7
        assert config.answer_temperature == 0.3
        assert config.enable_search is True
        assert config.enable_retrieve is True
        assert config.enable_calculate is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReActConfig(
            max_iterations=10,
            thought_temperature=0.5,
            enable_calculate=True,
        )

        assert config.max_iterations == 10
        assert config.thought_temperature == 0.5
        assert config.enable_calculate is True

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "max_iterations": 3,
            "thought_temperature": 0.8,
            "enable_search": False,
            "top_k": 10,
        }

        config = ReActConfig.from_dict(data)

        assert config.max_iterations == 3
        assert config.thought_temperature == 0.8
        assert config.enable_search is False
        assert config.top_k == 10


class TestReActAgent:
    """Tests for ReActAgent."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(return_value=[
            RetrievedChunk(
                content="Python is a high-level programming language.",
                score=0.9,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
            ),
        ])
        return retriever

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that follows ReAct format."""
        llm = AsyncMock()

        # First call: think + action
        # Second call: think + answer
        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return LLMResponse(
                    content="Thought: I need to search for information about Python.\nAction: search[Python programming language]",
                    model="gpt-4o-mini",
                    usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                )
            else:
                return LLMResponse(
                    content="Thought: I now have enough information to answer.\nAnswer: Python is a high-level programming language used for various applications.",
                    model="gpt-4o-mini",
                    usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                )

        llm.generate = mock_generate
        return llm

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock prompt manager."""
        manager = MagicMock()
        manager.get_system_prompt = MagicMock(return_value="You are helpful.")
        return manager

    @pytest.fixture
    def agent(self, mock_retriever, mock_llm, mock_prompt_manager):
        """Create a ReAct agent."""
        return ReActAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
        )

    def test_create_agent(self, mock_retriever, mock_llm):
        """Test creating a ReAct agent."""
        agent = ReActAgent(
            retriever=mock_retriever,
            llm=mock_llm,
        )

        assert agent.name == "react"
        assert agent.retriever == mock_retriever
        assert agent.llm == mock_llm

    def test_create_agent_with_config(self, mock_retriever, mock_llm):
        """Test creating agent with custom config."""
        config = ReActConfig(max_iterations=3)
        agent = ReActAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            config=config,
        )

        assert agent.react_config.max_iterations == 3

    def test_default_tools_initialized(self, agent):
        """Test that default tools are initialized."""
        assert "search" in agent._tools
        assert "retrieve" in agent._tools
        # calculate is disabled by default
        assert "calculate" not in agent._tools

    def test_add_custom_tool(self, agent):
        """Test adding a custom tool."""
        async def custom_handler(input, config_id, state):
            return "custom result"

        tool = Tool(
            name="custom",
            description="A custom tool",
            tool_type=ToolType.LOOKUP,
            handler=custom_handler,
        )

        agent.add_tool(tool)

        assert "custom" in agent._tools
        assert agent._tools["custom"].description == "A custom tool"

    @pytest.mark.asyncio
    async def test_run_basic(self, agent, mock_retriever, mock_llm):
        """Test basic agent run."""
        response = await agent.run(
            query="What is Python?",
            config_id="test-config",
        )

        assert isinstance(response, AgentResponse)
        assert len(response.answer) > 0
        assert "Python" in response.answer or "programming" in response.answer

    @pytest.mark.asyncio
    async def test_run_tracks_iterations(self, agent):
        """Test that run tracks iterations."""
        response = await agent.run(
            query="What is Python?",
            config_id="cfg",
        )

        assert "iterations" in response.metadata
        assert response.metadata["iterations"] > 0

    @pytest.mark.asyncio
    async def test_run_includes_thoughts(self, agent):
        """Test that run includes thoughts in metadata."""
        response = await agent.run(
            query="What is Python?",
            config_id="cfg",
        )

        assert "thoughts" in response.metadata
        assert len(response.metadata["thoughts"]) > 0

    @pytest.mark.asyncio
    async def test_run_includes_actions(self, agent):
        """Test that run includes actions in metadata."""
        response = await agent.run(
            query="What is Python?",
            config_id="cfg",
        )

        assert "actions" in response.metadata

    @pytest.mark.asyncio
    async def test_run_with_max_iterations(self, mock_retriever, mock_prompt_manager):
        """Test run respects max iterations."""
        # Create LLM that never wants to answer
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=LLMResponse(
            content="Thought: I need more information.\nAction: search[more info]",
            model="test",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        ))

        config = ReActConfig(max_iterations=2)
        agent = ReActAgent(
            retriever=mock_retriever,
            llm=llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        # Should stop after max iterations
        assert response.metadata["iterations"] <= 3  # +1 for answer step

    @pytest.mark.asyncio
    async def test_search_tool(self, agent, mock_retriever):
        """Test search tool execution."""
        state: ReActState = {
            "query": "test",
            "config_id": "cfg",
            "retrieved_chunks": [],
        }

        result = await agent._search_tool("Python", "cfg", state)

        assert len(result) > 0
        mock_retriever.retrieve.assert_called()

    @pytest.mark.asyncio
    async def test_calculate_tool(self, mock_retriever, mock_llm, mock_prompt_manager):
        """Test calculate tool."""
        config = ReActConfig(enable_calculate=True)
        agent = ReActAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        state: ReActState = {"query": "test", "config_id": "cfg"}

        result = await agent._calculate_tool("2 + 2", "cfg", state)

        assert "4" in result

    @pytest.mark.asyncio
    async def test_calculate_tool_invalid_expression(self, mock_retriever, mock_llm, mock_prompt_manager):
        """Test calculate tool with invalid expression."""
        config = ReActConfig(enable_calculate=True)
        agent = ReActAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        state: ReActState = {"query": "test", "config_id": "cfg"}

        # Try to use invalid characters
        result = await agent._calculate_tool("import os", "cfg", state)

        assert "Error" in result or "Invalid" in result

    @pytest.mark.asyncio
    async def test_stream(self, agent):
        """Test streaming response."""
        chunks = []
        async for chunk in agent.stream(
            query="What is Python?",
            config_id="cfg",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0


class TestReActParsing:
    """Tests for ReAct response parsing."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing parsing."""
        retriever = AsyncMock()
        llm = AsyncMock()
        return ReActAgent(retriever=retriever, llm=llm)

    def test_parse_thought_and_action(self, agent):
        """Test parsing thought and action."""
        response = """Thought: I need to search for information about Python.
Action: search[Python programming]"""

        thought, action, answer = agent._parse_response(response)

        assert "search for information" in thought
        assert "search[Python programming]" in action
        assert answer == ""

    def test_parse_thought_and_answer(self, agent):
        """Test parsing thought and answer."""
        response = """Thought: I now have enough information.
Answer: Python is a programming language."""

        thought, action, answer = agent._parse_response(response)

        assert "enough information" in thought
        assert action == ""
        assert "Python is a programming language" in answer

    def test_parse_action_format(self, agent):
        """Test parsing action format."""
        # Standard format
        tool, input = agent._parse_action("search[Python programming]")
        assert tool == "search"
        assert input == "Python programming"

        # With parentheses
        tool, input = agent._parse_action("retrieve(machine learning)")
        assert tool == "retrieve"
        assert input == "machine learning"

    def test_parse_action_fallback(self, agent):
        """Test action parsing fallback."""
        # Plain text becomes search
        tool, input = agent._parse_action("just some text")
        assert tool == "search"
        assert input == "just some text"


class TestReActState:
    """Tests for ReActState."""

    def test_create_state(self):
        """Test creating ReAct state."""
        state: ReActState = {
            "query": "What is Python?",
            "config_id": "cfg-123",
            "thoughts": [],
            "actions": [],
            "observations": [],
            "iterations": 0,
            "max_iterations": 5,
            "context": [],
            "answer": "",
            "should_answer": False,
        }

        assert state["query"] == "What is Python?"
        assert state["iterations"] == 0
        assert state["should_answer"] is False

    def test_state_with_reasoning(self):
        """Test state with reasoning history."""
        state: ReActState = {
            "query": "Test",
            "config_id": "cfg",
            "thoughts": [Thought(content="Need info", iteration=0)],
            "actions": [Action(tool="search", input="test", iteration=0)],
            "observations": [Observation(content="Result", tool="search", iteration=0)],
            "iterations": 1,
        }

        assert len(state["thoughts"]) == 1
        assert len(state["actions"]) == 1
        assert len(state["observations"]) == 1


class TestReActHelpers:
    """Tests for ReAct helper methods."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing helpers."""
        retriever = AsyncMock()
        llm = AsyncMock()
        return ReActAgent(retriever=retriever, llm=llm)

    def test_format_reasoning_history(self, agent):
        """Test formatting reasoning history."""
        state: ReActState = {
            "query": "Test",
            "config_id": "cfg",
            "thoughts": [
                Thought(content="First thought", iteration=0),
                Thought(content="Second thought", iteration=1),
            ],
            "actions": [
                Action(tool="search", input="query1", iteration=0),
            ],
            "observations": [
                Observation(content="Result 1", tool="search", iteration=0),
            ],
        }

        history = agent._format_reasoning_history(state)

        assert "First thought" in history
        assert "search[query1]" in history
        assert "Result 1" in history

    def test_format_tools_description(self, agent):
        """Test formatting tools description."""
        description = agent._format_tools_description()

        assert "search" in description
        assert "retrieve" in description

    def test_should_continue_on_should_answer(self, agent):
        """Test _should_continue returns answer when should_answer is True."""
        state: ReActState = {
            "should_answer": True,
            "iterations": 1,
        }

        result = agent._should_continue(state)
        assert result == "answer"

    def test_should_continue_on_max_iterations(self, agent):
        """Test _should_continue returns answer on max iterations."""
        state: ReActState = {
            "should_answer": False,
            "iterations": 5,
            "max_iterations": 5,
        }

        result = agent._should_continue(state)
        assert result == "answer"

    def test_should_continue_on_error(self, agent):
        """Test _should_continue returns answer on error."""
        state: ReActState = {
            "should_answer": False,
            "iterations": 1,
            "error": "Something went wrong",
        }

        result = agent._should_continue(state)
        assert result == "answer"

    def test_should_continue_normally(self, agent):
        """Test _should_continue returns continue normally."""
        state: ReActState = {
            "should_answer": False,
            "iterations": 1,
            "max_iterations": 5,
        }

        result = agent._should_continue(state)
        assert result == "continue"


class TestReActSystemPrompt:
    """Tests for ReAct system prompt."""

    def test_system_prompt_contains_format(self):
        """Test system prompt contains expected format."""
        assert "Thought:" in REACT_SYSTEM_PROMPT
        assert "Action:" in REACT_SYSTEM_PROMPT
        assert "Observation:" in REACT_SYSTEM_PROMPT
        assert "Answer:" in REACT_SYSTEM_PROMPT

    def test_system_prompt_has_placeholders(self):
        """Test system prompt has placeholders."""
        assert "{tools}" in REACT_SYSTEM_PROMPT
        assert "{max_iterations}" in REACT_SYSTEM_PROMPT
