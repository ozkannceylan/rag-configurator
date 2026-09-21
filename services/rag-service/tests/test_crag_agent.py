"""Tests for CRAG (Corrective RAG) agent module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentResponse, StepType
from app.agents.crag import (
    QUERY_REWRITE_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    CRAGAgent,
    CRAGConfig,
    CRAGState,
    RelevanceEvaluation,
    RelevanceGrade,
)
from app.llm.base import LLMResponse, LLMUsage
from app.retrieval.base import RetrievedChunk


class TestRelevanceGrade:
    """Tests for RelevanceGrade enum."""

    def test_grade_values(self):
        """Test grade values."""
        assert RelevanceGrade.HIGHLY_RELEVANT.value == "highly_relevant"
        assert RelevanceGrade.RELEVANT.value == "relevant"
        assert RelevanceGrade.PARTIALLY_RELEVANT.value == "partially_relevant"
        assert RelevanceGrade.IRRELEVANT.value == "irrelevant"


class TestRelevanceEvaluation:
    """Tests for RelevanceEvaluation class."""

    def test_create_evaluation(self):
        """Test creating an evaluation."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.RELEVANT,
            score=0.8,
            reasoning="Documents contain relevant information",
            needs_correction=False,
        )

        assert evaluation.grade == RelevanceGrade.RELEVANT
        assert evaluation.score == 0.8
        assert evaluation.needs_correction is False

    def test_evaluation_with_chunk_scores(self):
        """Test evaluation with chunk scores."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.HIGHLY_RELEVANT,
            score=0.9,
            reasoning="Very relevant",
            needs_correction=False,
            chunk_scores={"c1": 0.95, "c2": 0.85},
        )

        assert evaluation.chunk_scores["c1"] == 0.95
        assert len(evaluation.chunk_scores) == 2

    def test_evaluation_needs_correction(self):
        """Test evaluation that needs correction."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.IRRELEVANT,
            score=0.3,
            reasoning="Documents do not address the question",
            needs_correction=True,
        )

        assert evaluation.needs_correction is True
        assert evaluation.grade == RelevanceGrade.IRRELEVANT


class TestCRAGConfig:
    """Tests for CRAGConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = CRAGConfig()

        assert config.relevance_threshold == 0.6
        assert config.high_relevance_threshold == 0.8
        assert config.max_rewrites == 2
        assert config.use_llm_evaluation is True
        assert config.use_score_evaluation is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = CRAGConfig(
            relevance_threshold=0.7,
            max_rewrites=3,
            expand_query=False,
        )

        assert config.relevance_threshold == 0.7
        assert config.max_rewrites == 3
        assert config.expand_query is False

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "relevance_threshold": 0.5,
            "max_rewrites": 1,
            "use_llm_evaluation": False,
            "top_k": 10,
        }

        config = CRAGConfig.from_dict(data)

        assert config.relevance_threshold == 0.5
        assert config.max_rewrites == 1
        assert config.use_llm_evaluation is False
        assert config.top_k == 10


class TestCRAGAgent:
    """Tests for CRAGAgent."""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever."""
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(
            return_value=[
                RetrievedChunk(
                    content="Python is a high-level programming language.",
                    score=0.9,
                    chunk_id="c1",
                    document_id="d1",
                    config_id="cfg",
                ),
                RetrievedChunk(
                    content="Python supports object-oriented programming.",
                    score=0.85,
                    chunk_id="c2",
                    document_id="d1",
                    config_id="cfg",
                ),
            ]
        )
        return retriever

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns relevant evaluation."""
        llm = AsyncMock()

        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1

            # Check if this is an evaluation call
            messages = args[0] if args else kwargs.get("messages", [])
            if messages and "GRADE:" in str(messages):
                return LLMResponse(
                    content="GRADE: relevant\nSCORE: 0.8\nREASONING: Documents are relevant.\nNEEDS_CORRECTION: no",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=50, completion_tokens=20, total_tokens=70
                    ),
                )
            else:
                return LLMResponse(
                    content="Python is a versatile programming language.",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=100, completion_tokens=50, total_tokens=150
                    ),
                )

        llm.generate = mock_generate
        return llm

    @pytest.fixture
    def mock_llm_poor_relevance(self):
        """Create a mock LLM that returns poor relevance initially."""
        llm = AsyncMock()

        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1

            messages = args[0] if args else kwargs.get("messages", [])

            # First evaluation returns poor relevance
            if call_count[0] == 1 and "GRADE:" in str(messages):
                return LLMResponse(
                    content="GRADE: irrelevant\nSCORE: 0.3\nREASONING: Documents don't match.\nNEEDS_CORRECTION: yes",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=50, completion_tokens=20, total_tokens=70
                    ),
                )
            # Query rewrite
            elif call_count[0] == 2:
                return LLMResponse(
                    content="Rewritten Query: What are Python programming language features?",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=50, completion_tokens=20, total_tokens=70
                    ),
                )
            # Second evaluation returns good relevance
            elif "GRADE:" in str(messages):
                return LLMResponse(
                    content="GRADE: relevant\nSCORE: 0.8\nREASONING: Now relevant.\nNEEDS_CORRECTION: no",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=50, completion_tokens=20, total_tokens=70
                    ),
                )
            # Final answer
            else:
                return LLMResponse(
                    content="Python is a programming language.",
                    model="gpt-4o-mini",
                    usage=LLMUsage(
                        prompt_tokens=100, completion_tokens=50, total_tokens=150
                    ),
                )

        llm.generate = mock_generate
        return llm

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create a mock prompt manager."""
        manager = MagicMock()
        manager.get_system_prompt = MagicMock(return_value="You are helpful.")
        manager.get_rag_prompt = MagicMock(
            return_value="Context: {context}\nQuery: {query}"
        )
        manager.format_context = MagicMock(return_value="[1] Python content...")
        manager.format_history = MagicMock(return_value="")
        return manager

    @pytest.fixture
    def agent(self, mock_retriever, mock_llm, mock_prompt_manager):
        """Create a CRAG agent."""
        return CRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            prompt_manager=mock_prompt_manager,
        )

    def test_create_agent(self, mock_retriever, mock_llm):
        """Test creating a CRAG agent."""
        agent = CRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
        )

        assert agent.name == "crag"
        assert agent.retriever == mock_retriever
        assert agent.llm == mock_llm

    def test_create_agent_with_config(self, mock_retriever, mock_llm):
        """Test creating agent with custom config."""
        config = CRAGConfig(max_rewrites=3, relevance_threshold=0.7)
        agent = CRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm,
            config=config,
        )

        assert agent.crag_config.max_rewrites == 3
        assert agent.crag_config.relevance_threshold == 0.7

    @pytest.mark.asyncio
    async def test_run_basic_relevant(self, agent, mock_retriever, mock_llm):
        """Test basic run with relevant retrieval."""
        response = await agent.run(
            query="What is Python?",
            config_id="test-config",
        )

        assert isinstance(response, AgentResponse)
        assert len(response.answer) > 0
        # Should not have rewritten (relevant on first try)
        assert response.metadata["rewrite_count"] == 0

    @pytest.mark.asyncio
    async def test_run_with_correction(
        self, mock_retriever, mock_llm_poor_relevance, mock_prompt_manager
    ):
        """Test run that requires query correction."""
        agent = CRAGAgent(
            retriever=mock_retriever,
            llm=mock_llm_poor_relevance,
            prompt_manager=mock_prompt_manager,
        )

        response = await agent.run(
            query="What is Python?",
            config_id="test-config",
        )

        assert isinstance(response, AgentResponse)
        # Should have rewritten at least once
        assert response.metadata["rewrite_count"] >= 1
        assert len(response.metadata["rewritten_queries"]) >= 1

    @pytest.mark.asyncio
    async def test_run_respects_max_rewrites(self, mock_retriever, mock_prompt_manager):
        """Test that run respects max_rewrites limit."""
        # Create LLM that always says irrelevant
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="GRADE: irrelevant\nSCORE: 0.2\nREASONING: Not relevant.\nNEEDS_CORRECTION: yes",
                model="test",
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        )

        config = CRAGConfig(max_rewrites=2)
        agent = CRAGAgent(
            retriever=mock_retriever,
            llm=llm,
            prompt_manager=mock_prompt_manager,
            config=config,
        )

        response = await agent.run(
            query="Test",
            config_id="cfg",
        )

        # Should stop after max_rewrites
        assert response.metadata["rewrite_count"] <= 2

    @pytest.mark.asyncio
    async def test_run_includes_evaluation(self, agent):
        """Test that run includes evaluation in metadata."""
        response = await agent.run(
            query="What is Python?",
            config_id="cfg",
        )

        assert "evaluation" in response.metadata
        assert response.metadata["evaluation"]["grade"] is not None
        assert response.metadata["evaluation"]["score"] is not None

    @pytest.mark.asyncio
    async def test_run_tracks_steps(self, agent):
        """Test that run tracks execution steps."""
        response = await agent.run(
            query="What is Python?",
            config_id="cfg",
        )

        step_types = [s.step_type for s in response.steps]
        assert StepType.RETRIEVE in step_types
        assert StepType.EVALUATE in step_types
        assert StepType.GENERATE in step_types

    @pytest.mark.asyncio
    async def test_evaluate_only(self, agent):
        """Test evaluate_only method."""
        evaluation = await agent.evaluate_only(
            query="What is Python?",
            config_id="cfg",
        )

        assert isinstance(evaluation, RelevanceEvaluation)
        assert evaluation.score > 0
        assert evaluation.grade is not None

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


class TestCRAGEvaluationParsing:
    """Tests for evaluation response parsing."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing parsing."""
        retriever = AsyncMock()
        llm = AsyncMock()
        return CRAGAgent(retriever=retriever, llm=llm)

    def test_parse_full_evaluation(self, agent):
        """Test parsing complete evaluation response."""
        response = """GRADE: relevant
SCORE: 0.85
REASONING: The documents contain specific information about Python programming.
NEEDS_CORRECTION: no"""

        grade, score, reasoning, needs_correction = agent._parse_evaluation(response)

        assert grade == RelevanceGrade.RELEVANT
        assert score == 0.85
        assert "Python" in reasoning
        assert needs_correction is False

    def test_parse_irrelevant_evaluation(self, agent):
        """Test parsing irrelevant evaluation."""
        response = """GRADE: irrelevant
SCORE: 0.2
REASONING: Documents don't address the question.
NEEDS_CORRECTION: yes"""

        grade, score, reasoning, needs_correction = agent._parse_evaluation(response)

        assert grade == RelevanceGrade.IRRELEVANT
        assert score == 0.2
        assert needs_correction is True

    def test_parse_highly_relevant(self, agent):
        """Test parsing highly relevant evaluation."""
        response = """GRADE: highly_relevant
SCORE: 0.95
REASONING: Perfect match.
NEEDS_CORRECTION: no"""

        grade, score, reasoning, needs_correction = agent._parse_evaluation(response)

        assert grade == RelevanceGrade.HIGHLY_RELEVANT
        assert score == 0.95

    def test_parse_partial_response(self, agent):
        """Test parsing partial response with defaults."""
        response = """GRADE: relevant
Some other text without proper format"""

        grade, score, reasoning, needs_correction = agent._parse_evaluation(response)

        assert grade == RelevanceGrade.RELEVANT
        # Should have default values for missing fields

    def test_parse_score_clamping(self, agent):
        """Test that scores are clamped to 0-1 range."""
        response = """GRADE: relevant
SCORE: 1.5
REASONING: Test
NEEDS_CORRECTION: no"""

        grade, score, reasoning, needs_correction = agent._parse_evaluation(response)

        assert score <= 1.0


class TestCRAGState:
    """Tests for CRAGState."""

    def test_create_state(self):
        """Test creating CRAG state."""
        state: CRAGState = {
            "query": "What is Python?",
            "original_query": "What is Python?",
            "config_id": "cfg-123",
            "rewrite_count": 0,
            "max_rewrites": 2,
            "rewritten_queries": [],
            "relevance_score": 0.0,
        }

        assert state["query"] == "What is Python?"
        assert state["rewrite_count"] == 0

    def test_state_with_evaluation(self):
        """Test state with evaluation."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.RELEVANT,
            score=0.8,
            reasoning="Good",
            needs_correction=False,
        )

        state: CRAGState = {
            "query": "Test",
            "config_id": "cfg",
            "evaluation": evaluation,
            "relevance_score": 0.8,
        }

        assert state["evaluation"].score == 0.8

    def test_state_with_rewrites(self):
        """Test state with rewritten queries."""
        state: CRAGState = {
            "query": "Rewritten query",
            "original_query": "Original query",
            "config_id": "cfg",
            "rewrite_count": 2,
            "rewritten_queries": ["First rewrite", "Second rewrite"],
        }

        assert state["rewrite_count"] == 2
        assert len(state["rewritten_queries"]) == 2


class TestCRAGRelevanceCheck:
    """Tests for relevance checking logic."""

    @pytest.fixture
    def agent(self):
        """Create agent for testing."""
        retriever = AsyncMock()
        llm = AsyncMock()
        return CRAGAgent(retriever=retriever, llm=llm)

    def test_check_relevance_relevant(self, agent):
        """Test check_relevance returns relevant for good score."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.RELEVANT,
            score=0.8,
            reasoning="Good",
            needs_correction=False,
        )

        state: CRAGState = {
            "evaluation": evaluation,
            "rewrite_count": 0,
            "max_rewrites": 2,
        }

        result = agent._check_relevance(state)
        assert result == "relevant"

    def test_check_relevance_irrelevant(self, agent):
        """Test check_relevance returns irrelevant for poor score."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.IRRELEVANT,
            score=0.3,
            reasoning="Poor",
            needs_correction=True,
        )

        state: CRAGState = {
            "evaluation": evaluation,
            "rewrite_count": 0,
            "max_rewrites": 2,
        }

        result = agent._check_relevance(state)
        assert result == "irrelevant"

    def test_check_relevance_max_rewrites(self, agent):
        """Test check_relevance returns relevant when max rewrites reached."""
        evaluation = RelevanceEvaluation(
            grade=RelevanceGrade.IRRELEVANT,
            score=0.3,
            reasoning="Still poor",
            needs_correction=True,
        )

        state: CRAGState = {
            "evaluation": evaluation,
            "rewrite_count": 2,
            "max_rewrites": 2,
        }

        # Should return relevant to proceed with generation
        result = agent._check_relevance(state)
        assert result == "relevant"

    def test_check_relevance_no_evaluation(self, agent):
        """Test check_relevance with no evaluation."""
        state: CRAGState = {
            "evaluation": None,
            "rewrite_count": 0,
        }

        # Should default to relevant
        result = agent._check_relevance(state)
        assert result == "relevant"


class TestCRAGPrompts:
    """Tests for CRAG prompts."""

    def test_evaluation_prompt_has_placeholders(self):
        """Test evaluation prompt has required placeholders."""
        assert "{query}" in RELEVANCE_EVALUATION_PROMPT
        assert "{context}" in RELEVANCE_EVALUATION_PROMPT

    def test_evaluation_prompt_has_format(self):
        """Test evaluation prompt contains expected format."""
        assert "GRADE:" in RELEVANCE_EVALUATION_PROMPT
        assert "SCORE:" in RELEVANCE_EVALUATION_PROMPT
        assert "REASONING:" in RELEVANCE_EVALUATION_PROMPT
        assert "NEEDS_CORRECTION:" in RELEVANCE_EVALUATION_PROMPT

    def test_rewrite_prompt_has_placeholders(self):
        """Test rewrite prompt has required placeholders."""
        assert "{query}" in QUERY_REWRITE_PROMPT
        assert "{context}" in QUERY_REWRITE_PROMPT
        assert "{previous_queries}" in QUERY_REWRITE_PROMPT
        assert "{evaluation}" in QUERY_REWRITE_PROMPT


class TestCRAGScoreEvaluation:
    """Tests for score-based evaluation."""

    @pytest.fixture
    def agent_score_only(self, mock_retriever):
        """Create agent with score-only evaluation."""
        llm = AsyncMock()
        llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="Answer",
                model="test",
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            )
        )

        config = CRAGConfig(
            use_llm_evaluation=False,
            use_score_evaluation=True,
        )
        return CRAGAgent(
            retriever=mock_retriever,
            llm=llm,
            config=config,
        )

    @pytest.fixture
    def mock_retriever(self):
        """Create mock retriever."""
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

    @pytest.mark.asyncio
    async def test_score_based_evaluation(self, agent_score_only):
        """Test evaluation using only retrieval scores."""
        response = await agent_score_only.run(
            query="Test",
            config_id="cfg",
        )

        assert isinstance(response, AgentResponse)
        # High score (0.9) should not trigger correction
        assert response.metadata["rewrite_count"] == 0
