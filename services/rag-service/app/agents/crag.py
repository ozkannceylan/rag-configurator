"""CRAG (Corrective RAG) agent implementation using LangGraph."""

import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypedDict

from app.agents.base import (
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentStep,
    BaseAgent,
    StepType,
)
from app.llm.base import BaseLLM, Message
from app.prompts.manager import PromptManager
from app.retrieval.base import BaseRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class RelevanceGrade(StrEnum):
    """Relevance grade for retrieved documents."""

    HIGHLY_RELEVANT = "highly_relevant"
    RELEVANT = "relevant"
    PARTIALLY_RELEVANT = "partially_relevant"
    IRRELEVANT = "irrelevant"


@dataclass
class RelevanceEvaluation:
    """Result of relevance evaluation."""

    grade: RelevanceGrade
    score: float  # 0-1
    reasoning: str
    needs_correction: bool
    chunk_scores: dict[str, float] = field(default_factory=dict)


class CRAGState(TypedDict, total=False):
    """State for CRAG agent execution."""

    # Input
    query: str
    original_query: str
    config_id: str
    conversation_history: list[dict[str, str]]

    # Retrieval
    retrieved_chunks: list[RetrievedChunk]
    context: str

    # Evaluation
    evaluation: RelevanceEvaluation | None
    relevance_score: float

    # Correction
    rewrite_count: int
    max_rewrites: int
    rewritten_queries: list[str]

    # Generation
    answer: str
    sources: list[RetrievedChunk]

    # Tracking
    steps: list[AgentStep]
    error: str | None
    metadata: dict[str, Any]


@dataclass
class CRAGConfig(AgentConfig):
    """Configuration specific to CRAG agent."""

    # Relevance thresholds
    relevance_threshold: float = 0.6  # Below this triggers correction
    high_relevance_threshold: float = 0.8  # Above this skips correction

    # Correction settings
    max_rewrites: int = 2
    rewrite_temperature: float = 0.7

    # Evaluation settings
    use_llm_evaluation: bool = True  # Use LLM to grade relevance
    use_score_evaluation: bool = True  # Also use retrieval scores
    evaluation_temperature: float = 0.3

    # Query expansion
    expand_query: bool = True  # Expand query on rewrite

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CRAGConfig":
        """Create from dictionary."""
        base = AgentConfig.from_dict(data)
        return cls(
            top_k=base.top_k,
            min_score=base.min_score,
            temperature=base.temperature,
            max_tokens=base.max_tokens,
            streaming=base.streaming,
            system_prompt_name=base.system_prompt_name,
            rag_prompt_name=base.rag_prompt_name,
            include_steps=base.include_steps,
            verbose=base.verbose,
            timeout_seconds=base.timeout_seconds,
            relevance_threshold=data.get("relevance_threshold", 0.6),
            high_relevance_threshold=data.get("high_relevance_threshold", 0.8),
            max_rewrites=data.get("max_rewrites", 2),
            rewrite_temperature=data.get("rewrite_temperature", 0.7),
            use_llm_evaluation=data.get("use_llm_evaluation", True),
            use_score_evaluation=data.get("use_score_evaluation", True),
            evaluation_temperature=data.get("evaluation_temperature", 0.3),
            expand_query=data.get("expand_query", True),
        )


# Evaluation prompt
RELEVANCE_EVALUATION_PROMPT = """Evaluate the relevance of the retrieved documents to the user's question.

Question: {query}

Retrieved Documents:
{context}

Evaluate each document's relevance and provide an overall assessment.

Respond in this exact format:
GRADE: [highly_relevant|relevant|partially_relevant|irrelevant]
SCORE: [0.0-1.0]
REASONING: [Brief explanation of why the documents are or aren't relevant]
NEEDS_CORRECTION: [yes|no]

Consider:
1. Do the documents contain information that directly addresses the question?
2. Is the information specific enough to formulate a good answer?
3. Are there gaps that would require additional retrieval?

Your evaluation:"""

# Query rewrite prompt
QUERY_REWRITE_PROMPT = """The retrieved documents were not relevant enough to answer the user's question.
Rewrite the query to improve retrieval results.

Original Question: {query}

Previous Queries Tried:
{previous_queries}

Retrieved Context (not relevant enough):
{context}

Relevance Assessment:
{evaluation}

Rewrite the query to:
1. Be more specific or use different terminology
2. Focus on the core information need
3. Add relevant context or constraints
{expand_instruction}

Rewritten Query:"""


class CRAGAgent(BaseAgent):
    """
    Corrective RAG (CRAG) agent.

    Implements self-correcting retrieval:
    Retrieve → Evaluate → (if poor) Rewrite & Re-retrieve → Generate

    Features:
    - LLM-based relevance evaluation
    - Automatic query rewriting for poor retrievals
    - Configurable relevance thresholds
    - Maximum rewrite limits to prevent loops
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: PromptManager | None = None,
        config: CRAGConfig | None = None,
    ):
        """
        Initialize CRAG agent.

        Args:
            retriever: Retriever for fetching documents
            llm: Language model for evaluation and generation
            prompt_manager: Prompt manager for templates
            config: CRAG configuration
        """
        super().__init__(config or CRAGConfig())
        self._agent_name = "crag"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.crag_config = config or CRAGConfig()

        # Build LangGraph if available
        self._graph = None
        self._use_langgraph = self._init_langgraph()

    def _init_langgraph(self) -> bool:
        """Initialize LangGraph if available."""
        try:
            # Availability probe: the import must stay so a missing LangGraph
            # raises ImportError here rather than later at call time.
            from langgraph.graph import END, StateGraph  # noqa: F401

            self._graph = self._build_graph()
            return True
        except ImportError:
            logger.info("LangGraph not available, using simple flow")
            return False

    def _build_graph(self):
        """Build the LangGraph state graph."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(CRAGState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("evaluate", self._evaluate_node)
        graph.add_node("rewrite_query", self._rewrite_query_node)
        graph.add_node("generate", self._generate_node)

        # Set entry point
        graph.set_entry_point("retrieve")

        # Add edges
        graph.add_edge("retrieve", "evaluate")

        # Conditional edge from evaluate
        graph.add_conditional_edges(
            "evaluate",
            self._check_relevance,
            {
                "relevant": "generate",
                "irrelevant": "rewrite_query",
            },
        )

        graph.add_edge("rewrite_query", "retrieve")
        graph.add_edge("generate", END)

        return graph.compile()

    def _check_relevance(self, state: CRAGState) -> str:
        """Check if retrieval is relevant enough."""
        evaluation = state.get("evaluation")
        rewrite_count = state.get("rewrite_count", 0)
        max_rewrites = state.get("max_rewrites", self.crag_config.max_rewrites)

        # If we've hit max rewrites, proceed to generate
        if rewrite_count >= max_rewrites:
            logger.info(
                f"Max rewrites ({max_rewrites}) reached, proceeding to generate"
            )
            return "relevant"

        # Check evaluation
        if evaluation is None:
            return "relevant"

        if evaluation.needs_correction:
            return "irrelevant"

        # Check score threshold
        if evaluation.score >= self.crag_config.relevance_threshold:
            return "relevant"

        return "irrelevant"

    async def _retrieve_node(self, state: CRAGState) -> CRAGState:
        """Retrieve relevant chunks."""
        start_time = time.time()

        query = state["query"]
        config_id = state["config_id"]

        try:
            chunks = await self.retriever.retrieve(
                query=query,
                config_id=config_id,
                top_k=self.config.top_k,
            )

            # Filter by min score
            if self.config.min_score > 0:
                chunks = [c for c in chunks if c.score >= self.config.min_score]

            # Format context
            context = self.prompt_manager.format_context(
                [c.to_dict() for c in chunks],
                format_type="numbered",
            )

            duration = (time.time() - start_time) * 1000

            # Create step
            step = AgentStep(
                step_type=StepType.RETRIEVE,
                name="retrieve_chunks",
                input={"query": query, "top_k": self.config.top_k},
                output={
                    "chunk_count": len(chunks),
                    "avg_score": (
                        sum(c.score for c in chunks) / len(chunks) if chunks else 0
                    ),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "retrieved_chunks": chunks,
                "context": context,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            step = AgentStep(
                step_type=StepType.ERROR,
                name="retrieve_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)
            return {
                **state,
                "retrieved_chunks": [],
                "context": "No context available.",
                "steps": steps,
                "error": str(e),
            }

    async def _evaluate_node(self, state: CRAGState) -> CRAGState:
        """Evaluate retrieval relevance."""
        start_time = time.time()

        query = state["query"]
        context = state.get("context", "")
        chunks = state.get("retrieved_chunks", [])

        try:
            evaluation = await self._evaluate_relevance(query, context, chunks)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.EVALUATE,
                name="evaluate_relevance",
                input={"query": query, "chunk_count": len(chunks)},
                output={
                    "grade": evaluation.grade.value,
                    "score": evaluation.score,
                    "needs_correction": evaluation.needs_correction,
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "evaluation": evaluation,
                "relevance_score": evaluation.score,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # On evaluation failure, proceed with generation
            evaluation = RelevanceEvaluation(
                grade=RelevanceGrade.RELEVANT,
                score=0.7,
                reasoning="Evaluation failed, proceeding with available context",
                needs_correction=False,
            )
            return {
                **state,
                "evaluation": evaluation,
                "relevance_score": 0.7,
            }

    async def _evaluate_relevance(
        self,
        query: str,
        context: str,
        chunks: list[RetrievedChunk],
    ) -> RelevanceEvaluation:
        """Evaluate relevance using LLM and/or scores."""
        # Start with score-based evaluation
        score_based_score = 0.0
        if chunks and self.crag_config.use_score_evaluation:
            avg_score = sum(c.score for c in chunks) / len(chunks)
            # Normalize to 0-1 range (assuming scores are already 0-1)
            score_based_score = min(1.0, avg_score)

        # LLM-based evaluation
        llm_score = 0.0
        llm_grade = RelevanceGrade.RELEVANT
        reasoning = ""

        if self.crag_config.use_llm_evaluation and context:
            prompt = RELEVANCE_EVALUATION_PROMPT.format(
                query=query,
                context=context[:3000],  # Limit context length
            )

            messages = [Message.user(prompt)]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.crag_config.evaluation_temperature,
                max_tokens=500,
            )

            llm_grade, llm_score, reasoning, needs_correction = self._parse_evaluation(
                response.content
            )
        else:
            needs_correction = score_based_score < self.crag_config.relevance_threshold
            reasoning = f"Score-based evaluation: {score_based_score:.2f}"

        # Combine scores
        if (
            self.crag_config.use_llm_evaluation
            and self.crag_config.use_score_evaluation
        ):
            final_score = (llm_score + score_based_score) / 2
        elif self.crag_config.use_llm_evaluation:
            final_score = llm_score
        else:
            final_score = score_based_score

        # Determine final grade
        if final_score >= self.crag_config.high_relevance_threshold:
            final_grade = RelevanceGrade.HIGHLY_RELEVANT
        elif final_score >= self.crag_config.relevance_threshold:
            final_grade = RelevanceGrade.RELEVANT
        elif final_score >= 0.4:
            final_grade = RelevanceGrade.PARTIALLY_RELEVANT
        else:
            final_grade = RelevanceGrade.IRRELEVANT

        # Build chunk scores
        chunk_scores = {c.chunk_id: c.score for c in chunks}

        # The grader is asked for an explicit NEEDS_CORRECTION verdict and
        # _parse_evaluation returns it, but this object used to be built from a
        # bare threshold comparison on a blended score, so the verdict never
        # reached the correction branch: CRAG would skip correction whenever the
        # blend cleared the threshold, even when the grader had said correction
        # was needed. The threshold is kept as a safety net, so this can only
        # make CRAG correct more often, never less.
        return RelevanceEvaluation(
            grade=final_grade,
            score=final_score,
            reasoning=reasoning,
            needs_correction=(
                needs_correction or final_score < self.crag_config.relevance_threshold
            ),
            chunk_scores=chunk_scores,
        )

    def _parse_evaluation(
        self,
        response: str,
    ) -> tuple[RelevanceGrade, float, str, bool]:
        """Parse LLM evaluation response."""
        grade = RelevanceGrade.RELEVANT
        score = 0.7
        reasoning = ""
        needs_correction = False

        # Parse grade
        grade_match = re.search(
            r"GRADE:\s*(highly_relevant|relevant|partially_relevant|irrelevant)",
            response,
            re.IGNORECASE,
        )
        if grade_match:
            grade_str = grade_match.group(1).lower()
            try:
                grade = RelevanceGrade(grade_str)
            except ValueError:
                pass

        # Parse score
        score_match = re.search(r"SCORE:\s*([\d.]+)", response)
        if score_match:
            try:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))
            except ValueError:
                pass

        # Parse reasoning
        reasoning_match = re.search(
            r"REASONING:\s*(.+?)(?=NEEDS_CORRECTION:|$)", response, re.DOTALL
        )
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()

        # Parse needs_correction
        correction_match = re.search(
            r"NEEDS_CORRECTION:\s*(yes|no)", response, re.IGNORECASE
        )
        if correction_match:
            needs_correction = correction_match.group(1).lower() == "yes"
        else:
            # Infer from grade/score
            needs_correction = grade in [
                RelevanceGrade.IRRELEVANT,
                RelevanceGrade.PARTIALLY_RELEVANT,
            ]

        return grade, score, reasoning, needs_correction

    async def _rewrite_query_node(self, state: CRAGState) -> CRAGState:
        """Rewrite query to improve retrieval."""
        start_time = time.time()

        query = state["query"]
        original_query = state.get("original_query", query)
        context = state.get("context", "")
        evaluation = state.get("evaluation")
        rewrite_count = state.get("rewrite_count", 0)
        previous_queries = state.get("rewritten_queries", [])

        try:
            # Build rewrite prompt
            expand_instruction = ""
            if self.crag_config.expand_query:
                expand_instruction = "4. Consider adding synonyms or related terms"

            evaluation_text = ""
            if evaluation:
                evaluation_text = f"Grade: {evaluation.grade.value}, Score: {evaluation.score:.2f}\nReason: {evaluation.reasoning}"

            prompt = QUERY_REWRITE_PROMPT.format(
                query=query,
                previous_queries="\n".join(f"- {q}" for q in previous_queries)
                or "None",
                context=context[:1500],
                evaluation=evaluation_text,
                expand_instruction=expand_instruction,
            )

            messages = [Message.user(prompt)]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.crag_config.rewrite_temperature,
                max_tokens=200,
            )

            # Extract rewritten query
            rewritten_query = response.content.strip()
            # Clean up common prefixes
            for prefix in ["Rewritten Query:", "Query:", "New Query:"]:
                if rewritten_query.startswith(prefix):
                    rewritten_query = rewritten_query[len(prefix) :].strip()

            # Remove quotes if present
            rewritten_query = rewritten_query.strip("\"'")

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.REWRITE,
                name="rewrite_query",
                input={"original_query": query},
                output={"rewritten_query": rewritten_query},
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            # Update previous queries
            new_previous_queries = list(previous_queries)
            new_previous_queries.append(query)

            return {
                **state,
                "query": rewritten_query,
                "original_query": original_query,
                "rewrite_count": rewrite_count + 1,
                "rewritten_queries": new_previous_queries,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return {
                **state,
                "rewrite_count": rewrite_count
                + 1,  # Increment to prevent infinite loop
            }

    async def _generate_node(self, state: CRAGState) -> CRAGState:
        """Generate final answer."""
        start_time = time.time()

        query = state.get("original_query", state["query"])
        context = state.get("context", "")
        history = state.get("conversation_history", [])

        try:
            # Get system prompt
            system_prompt = self.prompt_manager.get_system_prompt(
                name=self.config.system_prompt_name
            )

            # Get RAG prompt with context
            history_str = self.prompt_manager.format_history(history) if history else ""
            rag_prompt = self.prompt_manager.get_rag_prompt(
                context=context,
                query=query,
                name=self.config.rag_prompt_name,
                history=history_str,
            )

            messages = [
                Message.system(system_prompt),
                Message.user(rag_prompt),
            ]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.GENERATE,
                name="generate_answer",
                input={"context_length": len(context), "query": query},
                output={
                    "answer_length": len(response.content),
                    "model": response.model,
                },
                duration_ms=duration,
                metadata={
                    "prompt_tokens": (
                        response.usage.prompt_tokens if response.usage else 0
                    ),
                    "completion_tokens": (
                        response.usage.completion_tokens if response.usage else 0
                    ),
                },
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "answer": response.content,
                "sources": state.get("retrieved_chunks", []),
                "steps": steps,
                "metadata": {
                    **state.get("metadata", {}),
                    "model": response.model,
                    "usage": response.usage.to_dict() if response.usage else None,
                },
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            step = AgentStep(
                step_type=StepType.ERROR,
                name="generate_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)
            return {
                **state,
                "answer": "I apologize, but I encountered an error generating a response.",
                "steps": steps,
                "error": str(e),
            }

    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the CRAG agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and correction history
        """
        start_time = time.time()

        # Initial state
        initial_state: CRAGState = {
            "query": query,
            "original_query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "retrieved_chunks": [],
            "context": "",
            "evaluation": None,
            "relevance_score": 0.0,
            "rewrite_count": 0,
            "max_rewrites": self.crag_config.max_rewrites,
            "rewritten_queries": [],
            "answer": "",
            "sources": [],
            "steps": [],
            "metadata": {},
        }

        try:
            if self._use_langgraph and self._graph is not None:
                final_state = await self._graph.ainvoke(initial_state)
            else:
                final_state = await self._simple_flow(initial_state)

            total_duration = (time.time() - start_time) * 1000

            # Build response
            response = AgentResponse(
                answer=final_state.get("answer", ""),
                sources=self._format_sources(final_state.get("sources", [])),
                steps=final_state.get("steps", []) if self.config.include_steps else [],
                total_duration_ms=total_duration,
                metadata={
                    "rewrite_count": final_state.get("rewrite_count", 0),
                    "rewritten_queries": final_state.get("rewritten_queries", []),
                    "final_relevance_score": final_state.get("relevance_score", 0),
                    "evaluation": (
                        {
                            "grade": (
                                final_state["evaluation"].grade.value
                                if final_state.get("evaluation")
                                else None
                            ),
                            "score": (
                                final_state["evaluation"].score
                                if final_state.get("evaluation")
                                else None
                            ),
                            "reasoning": (
                                final_state["evaluation"].reasoning
                                if final_state.get("evaluation")
                                else None
                            ),
                        }
                        if final_state.get("evaluation")
                        else None
                    ),
                    **final_state.get("metadata", {}),
                },
            )

            # Add token usage from metadata
            if final_state.get("metadata", {}).get("usage"):
                usage = final_state["metadata"]["usage"]
                response.prompt_tokens = usage.get("prompt_tokens", 0)
                response.completion_tokens = usage.get("completion_tokens", 0)
                response.total_tokens = usage.get("total_tokens", 0)

            return response

        except Exception as e:
            logger.error(f"CRAG agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: CRAGState) -> CRAGState:
        """Execute CRAG flow without LangGraph."""
        while True:
            # Retrieve
            state = await self._retrieve_node(state)

            # Evaluate
            state = await self._evaluate_node(state)

            # Check if we should rewrite
            if self._check_relevance(state) == "irrelevant":
                state = await self._rewrite_query_node(state)
                # Loop back to retrieve
                continue

            # Generate and exit
            break

        state = await self._generate_node(state)
        return state

    async def stream(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream the agent response.

        Note: CRAG agent streams the final answer generation.
        """
        # Run the correction loop first
        response = await self.run(
            query=query,
            config_id=config_id,
            conversation_history=conversation_history,
            **kwargs,
        )

        # Yield the answer in chunks
        words = response.answer.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    async def evaluate_only(
        self,
        query: str,
        config_id: str,
    ) -> RelevanceEvaluation:
        """
        Evaluate retrieval relevance without generating answer.

        Useful for debugging or analysis.

        Returns:
            RelevanceEvaluation with score and reasoning
        """
        chunks = await self.retriever.retrieve(
            query=query,
            config_id=config_id,
            top_k=self.config.top_k,
        )

        context = self.prompt_manager.format_context(
            [c.to_dict() for c in chunks],
            format_type="numbered",
        )

        return await self._evaluate_relevance(query, context, chunks)

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self.retriever, "close"):
            await self.retriever.close()
        if hasattr(self.llm, "close"):
            await self.llm.close()
