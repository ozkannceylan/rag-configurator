"""Self-RAG agent implementation using LangGraph."""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, TypedDict

from app.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentStep,
    StepType,
)
from app.llm.base import BaseLLM, Message
from app.prompts.manager import PromptManager
from app.retrieval.base import BaseRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class RetrievalDecision(str, Enum):
    """Decision on whether retrieval is needed."""

    YES = "yes"
    NO = "no"


class SupportVerdict(str, Enum):
    """Verdict on whether answer is supported by context."""

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"


class UtilityVerdict(str, Enum):
    """Verdict on whether answer is useful."""

    USEFUL = "useful"
    PARTIALLY_USEFUL = "partially_useful"
    NOT_USEFUL = "not_useful"


@dataclass
class SelfRAGCritique:
    """Critique of generated answer."""

    retrieval_needed: bool
    relevance_verdict: str
    support_verdict: SupportVerdict
    utility_verdict: UtilityVerdict
    critique_text: str
    score: float  # 0-1 overall score
    refinements: int = 0


class SelfRAGState(TypedDict, total=False):
    """State for Self-RAG agent execution."""

    # Input
    query: str
    config_id: str
    conversation_history: List[Dict[str, str]]

    # Retrieval decision
    needs_retrieval: bool
    retrieval_decision_reason: str

    # Retrieval
    retrieved_chunks: List[RetrievedChunk]
    context: str

    # Generation
    answer: str
    sources: List[RetrievedChunk]

    # Critique
    critique: Optional[SelfRAGCritique]
    is_supported: bool
    is_useful: bool
    refinements: int
    max_refinements: int

    # Tracking
    steps: List[AgentStep]
    error: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class SelfRAGConfig(AgentConfig):
    """Configuration specific to Self-RAG agent."""

    # Decision thresholds
    retrieval_decision_threshold: float = 0.5
    support_threshold: float = 0.7
    utility_threshold: float = 0.6

    # Refinement settings
    max_refinements: int = 2
    refinement_temperature: float = 0.7

    # Prompts
    use_llm_critique: bool = True
    critique_temperature: float = 0.3

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SelfRAGConfig":
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
            retrieval_decision_threshold=data.get("retrieval_decision_threshold", 0.5),
            support_threshold=data.get("support_threshold", 0.7),
            utility_threshold=data.get("utility_threshold", 0.6),
            max_refinements=data.get("max_refinements", 2),
            refinement_temperature=data.get("refinement_temperature", 0.7),
            use_llm_critique=data.get("use_llm_critique", True),
            critique_temperature=data.get("critique_temperature", 0.3),
        )


# Decision prompt for whether retrieval is needed
RETRIEVAL_DECISION_PROMPT = """Determine if the following question requires retrieval from a knowledge base to answer accurately.

Question: {query}

Consider:
1. Is this a factual question requiring specific knowledge?
2. Is this about general knowledge that can be answered directly?
3. Would additional context improve the answer quality?

Respond with:
DECISION: [yes|no]
REASON: [brief explanation]

Your response:"""

# Critique prompt for evaluating answer quality
CRITIQUE_PROMPT = """Critique the following answer based on the retrieved context.

Question: {query}

Retrieved Context:
{context}

Generated Answer:
{answer}

Evaluate on:
1. RELEVANCE: Does the retrieved context relate to the question? (high|medium|low)
2. SUPPORT: Is the answer fully supported by the context? (supported|partially_supported|unsupported)
3. UTILITY: Is the answer helpful and complete? (useful|partially_useful|not_useful)
4. OVERALL SCORE: Rate 0-1
5. CRITIQUE: Brief explanation of issues found

Respond in this format:
RELEVANCE: [high|medium|low]
SUPPORT: [supported|partially_supported|unsupported]
UTILITY: [useful|partially_useful|not_useful]
SCORE: [0.0-1.0]
CRITIQUE: [your critique]
NEEDS_REFINEMENT: [yes|no]

Your critique:"""

# Refinement prompt for improving answer
REFINEMENT_PROMPT = """Improve the answer based on the critique provided.

Question: {query}

Retrieved Context:
{context}

Previous Answer:
{answer}

Critique:
{critique}

Generate a refined answer that:
1. Addresses all issues mentioned in the critique
2. Uses the retrieved context more effectively
3. Provides a more accurate and complete response

Refined Answer:"""


class SelfRAGAgent(BaseAgent):
    """
    Self-Reflective RAG agent.

    Implements self-correction with multiple decision points:
    Query → Need Retrieval? → Retrieve → Generate → Critique → (refine) → Answer

    Key decisions:
    1. Does this query need retrieval?
    2. Is retrieved context relevant?
    3. Is the answer supported by context?
    4. Is the answer useful and complete?
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: Optional[PromptManager] = None,
        config: Optional[SelfRAGConfig] = None,
    ):
        """
        Initialize Self-RAG agent.

        Args:
            retriever: Retriever for fetching documents
            llm: Language model for generation and critique
            prompt_manager: Prompt manager for templates
            config: Self-RAG configuration
        """
        super().__init__(config or SelfRAGConfig())
        self._agent_name = "self_rag"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.selfrag_config = config or SelfRAGConfig()

        # Build LangGraph if available
        self._graph = None
        self._use_langgraph = self._init_langgraph()

    def _init_langgraph(self) -> bool:
        """Initialize LangGraph if available."""
        try:
            from langgraph.graph import StateGraph, END

            self._graph = self._build_graph()
            return True
        except ImportError:
            logger.info("LangGraph not available, using simple flow")
            return False

    def _build_graph(self):
        """Build the LangGraph state graph."""
        from langgraph.graph import StateGraph, END

        graph = StateGraph(SelfRAGState)

        # Add nodes
        graph.add_node("check_retrieval", self._check_retrieval_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("critique", self._critique_node)
        graph.add_node("refine", self._refine_node)

        # Set entry point
        graph.set_entry_point("check_retrieval")

        # Conditional edge: check_retrieval → retrieve or generate
        graph.add_conditional_edges(
            "check_retrieval",
            self._needs_retrieval,
            {"yes": "retrieve", "no": "generate"}
        )

        # Standard edges
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "critique")

        # Conditional edge: critique → END or refine
        graph.add_conditional_edges(
            "critique",
            self._is_good_answer,
            {"good": END, "refine": "refine"}
        )

        graph.add_edge("refine", "generate")

        return graph.compile()

    def _needs_retrieval(self, state: SelfRAGState) -> str:
        """Determine if retrieval is needed."""
        needs_retrieval = state.get("needs_retrieval", True)
        return "yes" if needs_retrieval else "no"

    def _is_good_answer(self, state: SelfRAGState) -> str:
        """Determine if answer is good enough or needs refinement."""
        critique = state.get("critique")
        refinements = state.get("refinements", 0)
        max_refinements = state.get("max_refinements", self.selfrag_config.max_refinements)

        # Check if max refinements reached
        if refinements >= max_refinements:
            logger.info(f"Max refinements ({max_refinements}) reached")
            return "good"

        # Check critique
        if critique is None:
            return "good"

        # Check if answer is supported and useful
        is_good = (
            critique.support_verdict == SupportVerdict.SUPPORTED and
            critique.utility_verdict in [UtilityVerdict.USEFUL, UtilityVerdict.PARTIALLY_USEFUL]
        )

        return "good" if is_good else "refine"

    async def _check_retrieval_node(self, state: SelfRAGState) -> SelfRAGState:
        """Check if retrieval is needed for this query."""
        start_time = time.time()

        query = state["query"]

        try:
            # Use LLM to decide if retrieval is needed
            prompt = RETRIEVAL_DECISION_PROMPT.format(query=query)
            messages = [Message.user(prompt)]

            response = await self.llm.generate(
                messages=messages,
                temperature=0.3,
                max_tokens=150,
            )

            # Parse decision
            needs_retrieval, reason = self._parse_retrieval_decision(response.content)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.EVALUATE,
                name="check_retrieval_needed",
                input={"query": query},
                output={"needs_retrieval": needs_retrieval, "reason": reason},
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "needs_retrieval": needs_retrieval,
                "retrieval_decision_reason": reason,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Retrieval decision failed: {e}")
            # Default to needing retrieval on error
            return {
                **state,
                "needs_retrieval": True,
                "retrieval_decision_reason": f"Error: {str(e)}",
            }

    def _parse_retrieval_decision(self, response: str) -> tuple[bool, str]:
        """Parse retrieval decision from LLM response."""
        needs_retrieval = True  # Default to yes
        reason = ""

        # Parse decision
        decision_match = re.search(r"DECISION:\s*(yes|no)", response, re.IGNORECASE)
        if decision_match:
            needs_retrieval = decision_match.group(1).lower() == "yes"

        # Parse reason
        reason_match = re.search(r"REASON:\s*(.+?)(?:\n|$)", response, re.DOTALL | re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()

        return needs_retrieval, reason

    async def _retrieve_node(self, state: SelfRAGState) -> SelfRAGState:
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

            step = AgentStep(
                step_type=StepType.RETRIEVE,
                name="retrieve_chunks",
                input={"query": query, "top_k": self.config.top_k},
                output={"chunk_count": len(chunks)},
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
            return {
                **state,
                "retrieved_chunks": [],
                "context": "No context available.",
                "error": str(e),
            }

    async def _generate_node(self, state: SelfRAGState) -> SelfRAGState:
        """Generate answer from context."""
        start_time = time.time()

        query = state["query"]
        context = state.get("context", "")
        history = state.get("conversation_history", [])
        needs_retrieval = state.get("needs_retrieval", True)

        try:
            # Get system prompt
            system_prompt = self.prompt_manager.get_system_prompt(
                name=self.config.system_prompt_name
            )

            # Build user prompt
            if needs_retrieval and context:
                # RAG prompt with context
                history_str = self.prompt_manager.format_history(history) if history else ""
                user_prompt = self.prompt_manager.get_rag_prompt(
                    context=context,
                    query=query,
                    name=self.config.rag_prompt_name,
                    history=history_str,
                )
            else:
                # Direct answer prompt without retrieval
                user_prompt = f"Question: {query}\n\nAnswer:"

            messages = [
                Message.system(system_prompt),
                Message.user(user_prompt),
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
                input={
                    "query": query,
                    "has_context": bool(context),
                    "retrieval_used": needs_retrieval,
                },
                output={
                    "answer_length": len(response.content),
                    "model": response.model,
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "answer": response.content,
                "sources": state.get("retrieved_chunks", []),
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                **state,
                "answer": "I apologize, but I encountered an error generating a response.",
                "error": str(e),
            }

    async def _critique_node(self, state: SelfRAGState) -> SelfRAGState:
        """Critique the generated answer."""
        start_time = time.time()

        query = state["query"]
        answer = state.get("answer", "")
        context = state.get("context", "")
        needs_retrieval = state.get("needs_retrieval", True)

        # Skip critique if no retrieval was needed
        if not needs_retrieval:
            critique = SelfRAGCritique(
                retrieval_needed=False,
                relevance_verdict="high",
                support_verdict=SupportVerdict.SUPPORTED,
                utility_verdict=UtilityVerdict.USEFUL,
                critique_text="Direct answer without retrieval",
                score=1.0,
            )
            return {
                **state,
                "critique": critique,
                "is_supported": True,
                "is_useful": True,
            }

        try:
            if self.selfrag_config.use_llm_critique and context:
                # Use LLM to critique
                prompt = CRITIQUE_PROMPT.format(
                    query=query,
                    context=context[:3000],  # Limit context length
                    answer=answer,
                )

                messages = [Message.user(prompt)]

                response = await self.llm.generate(
                    messages=messages,
                    temperature=self.selfrag_config.critique_temperature,
                    max_tokens=400,
                )

                critique = self._parse_critique(response.content)
            else:
                # Simple heuristic critique
                has_context = bool(context and len(context) > 50)
                answer_uses_context = any(
                    chunk.get("content", "")[:50] in answer
                    for chunk in state.get("retrieved_chunks", [])
                )

                critique = SelfRAGCritique(
                    retrieval_needed=True,
                    relevance_verdict="medium" if has_context else "low",
                    support_verdict=SupportVerdict.SUPPORTED if answer_uses_context else SupportVerdict.PARTIALLY_SUPPORTED,
                    utility_verdict=UtilityVerdict.USEFUL if len(answer) > 100 else UtilityVerdict.PARTIALLY_USEFUL,
                    critique_text="Heuristic evaluation" if not self.selfrag_config.use_llm_critique else "No context available",
                    score=0.7 if answer_uses_context else 0.5,
                )

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.EVALUATE,
                name="critique_answer",
                input={"answer_length": len(answer)},
                output={
                    "score": critique.score,
                    "support": critique.support_verdict.value,
                    "utility": critique.utility_verdict.value,
                    "needs_refinement": not (
                        critique.support_verdict == SupportVerdict.SUPPORTED and
                        critique.utility_verdict in [UtilityVerdict.USEFUL, UtilityVerdict.PARTIALLY_USEFUL]
                    ),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "critique": critique,
                "is_supported": critique.support_verdict == SupportVerdict.SUPPORTED,
                "is_useful": critique.utility_verdict in [UtilityVerdict.USEFUL, UtilityVerdict.PARTIALLY_USEFUL],
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Critique failed: {e}")
            # Default to accepting answer on critique failure
            critique = SelfRAGCritique(
                retrieval_needed=True,
                relevance_verdict="medium",
                support_verdict=SupportVerdict.SUPPORTED,
                utility_verdict=UtilityVerdict.USEFUL,
                critique_text=f"Critique error: {str(e)}",
                score=0.7,
            )
            return {
                **state,
                "critique": critique,
                "is_supported": True,
                "is_useful": True,
            }

    def _parse_critique(self, response: str) -> SelfRAGCritique:
        """Parse critique from LLM response."""
        # Default values
        relevance = "medium"
        support = SupportVerdict.PARTIALLY_SUPPORTED
        utility = UtilityVerdict.PARTIALLY_USEFUL
        score = 0.6
        critique_text = ""
        needs_refinement = False

        # Parse relevance
        relevance_match = re.search(r"RELEVANCE:\s*(high|medium|low)", response, re.IGNORECASE)
        if relevance_match:
            relevance = relevance_match.group(1).lower()

        # Parse support
        support_match = re.search(
            r"SUPPORT:\s*(supported|partially_supported|unsupported)",
            response,
            re.IGNORECASE
        )
        if support_match:
            support_str = support_match.group(1).lower()
            try:
                support = SupportVerdict(support_str)
            except ValueError:
                pass

        # Parse utility
        utility_match = re.search(
            r"UTILITY:\s*(useful|partially_useful|not_useful)",
            response,
            re.IGNORECASE
        )
        if utility_match:
            utility_str = utility_match.group(1).lower()
            try:
                utility = UtilityVerdict(utility_str)
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

        # Parse critique text
        critique_match = re.search(r"CRITIQUE:\s*(.+?)(?:NEEDS_REFINEMENT:|$)", response, re.DOTALL)
        if critique_match:
            critique_text = critique_match.group(1).strip()

        # Parse needs refinement
        refinement_match = re.search(r"NEEDS_REFINEMENT:\s*(yes|no)", response, re.IGNORECASE)
        if refinement_match:
            needs_refinement = refinement_match.group(1).lower() == "yes"
        else:
            # Infer from support/utility
            needs_refinement = support != SupportVerdict.SUPPORTED or utility == UtilityVerdict.NOT_USEFUL

        return SelfRAGCritique(
            retrieval_needed=True,
            relevance_verdict=relevance,
            support_verdict=support,
            utility_verdict=utility,
            critique_text=critique_text,
            score=score,
        )

    async def _refine_node(self, state: SelfRAGState) -> SelfRAGState:
        """Refine the answer based on critique."""
        start_time = time.time()

        query = state["query"]
        answer = state.get("answer", "")
        context = state.get("context", "")
        critique = state.get("critique")
        refinements = state.get("refinements", 0)

        try:
            if critique and self.selfrag_config.use_llm_critique:
                # Use LLM to refine
                prompt = REFINEMENT_PROMPT.format(
                    query=query,
                    context=context[:3000],
                    answer=answer,
                    critique=critique.critique_text,
                )

                messages = [Message.user(prompt)]

                response = await self.llm.generate(
                    messages=messages,
                    temperature=self.selfrag_config.refinement_temperature,
                    max_tokens=self.config.max_tokens,
                )

                refined_answer = response.content.strip()
            else:
                # Simple refinement - just note the issue
                refined_answer = f"{answer}\n\n[Note: This answer may need verification.]"

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.REFINE,
                name="refine_answer",
                input={"previous_answer_length": len(answer), "refinement": refinements + 1},
                output={"refined_answer_length": len(refined_answer)},
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            # Update critique with new refinement count
            if critique:
                critique.refinements = refinements + 1

            return {
                **state,
                "answer": refined_answer,
                "refinements": refinements + 1,
                "critique": critique,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return {
                **state,
                "refinements": refinements + 1,  # Increment to prevent infinite loop
            }

    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the Self-RAG agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and self-critique
        """
        start_time = time.time()

        # Initial state
        initial_state: SelfRAGState = {
            "query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "needs_retrieval": True,
            "retrieval_decision_reason": "",
            "retrieved_chunks": [],
            "context": "",
            "answer": "",
            "sources": [],
            "critique": None,
            "is_supported": False,
            "is_useful": False,
            "refinements": 0,
            "max_refinements": self.selfrag_config.max_refinements,
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
            critique = final_state.get("critique")
            metadata = {
                "needs_retrieval": final_state.get("needs_retrieval", True),
                "retrieval_reason": final_state.get("retrieval_decision_reason", ""),
                "refinements": final_state.get("refinements", 0),
                "critique": {
                    "score": critique.score if critique else None,
                    "support": critique.support_verdict.value if critique else None,
                    "utility": critique.utility_verdict.value if critique else None,
                    "critique_text": critique.critique_text if critique else None,
                } if critique else None,
                **final_state.get("metadata", {}),
            }

            response = AgentResponse(
                answer=final_state.get("answer", ""),
                sources=self._format_sources(final_state.get("sources", [])),
                steps=final_state.get("steps", []) if self.config.include_steps else [],
                total_duration_ms=total_duration,
                metadata=metadata,
            )

            # Add token usage from metadata
            if final_state.get("metadata", {}).get("usage"):
                usage = final_state["metadata"]["usage"]
                response.prompt_tokens = usage.get("prompt_tokens", 0)
                response.completion_tokens = usage.get("completion_tokens", 0)
                response.total_tokens = usage.get("total_tokens", 0)

            return response

        except Exception as e:
            logger.error(f"Self-RAG agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: SelfRAGState) -> SelfRAGState:
        """Execute Self-RAG flow without LangGraph."""
        # Check if retrieval is needed
        state = await self._check_retrieval_node(state)

        # Retrieve if needed
        if state.get("needs_retrieval", True):
            state = await self._retrieve_node(state)

        # Generate answer
        state = await self._generate_node(state)

        # Critique loop
        while True:
            state = await self._critique_node(state)

            # Check if good or max refinements reached
            if self._is_good_answer(state) == "good":
                break

            if state.get("refinements", 0) >= self.selfrag_config.max_refinements:
                break

            # Refine
            state = await self._refine_node(state)

        return state

    async def stream(
        self,
        query: str,
        config_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream the agent response.

        Note: Self-RAG agent streams the final answer generation.
        """
        # Run the self-critique loop first
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

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self.retriever, "close"):
            await self.retriever.close()
        if hasattr(self.llm, "close"):
            await self.llm.close()
