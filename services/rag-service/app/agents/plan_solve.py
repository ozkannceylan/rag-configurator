"""Plan-Solve agent implementation using LangGraph."""

import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
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


class PlanSolveState(TypedDict, total=False):
    """State for Plan-Solve agent execution."""

    # Input
    query: str
    config_id: str
    conversation_history: list[dict[str, str]]

    # Planning
    plan: list[str]  # List of sub-questions
    current_step: int
    max_steps: int

    # Execution
    step_results: list[str]  # Results from each step
    step_contexts: list[list[RetrievedChunk]]  # Context for each step

    # Synthesis
    synthesized_answer: str
    final_answer: str
    sources: list[RetrievedChunk]

    # Tracking
    steps: list[AgentStep]
    error: str | None
    metadata: dict[str, Any]


@dataclass
class PlanSolveConfig(AgentConfig):
    """Configuration specific to Plan-Solve agent."""

    # Planning settings
    max_steps: int = 5
    plan_temperature: float = 0.7

    # Step execution settings
    step_temperature: float = 0.5
    top_k_per_step: int = 3

    # Synthesis settings
    synthesis_temperature: float = 0.3

    # Whether to use retrieval for each step
    retrieve_per_step: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanSolveConfig":
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
            max_steps=data.get("max_steps", 5),
            plan_temperature=data.get("plan_temperature", 0.7),
            step_temperature=data.get("step_temperature", 0.5),
            top_k_per_step=data.get("top_k_per_step", 3),
            synthesis_temperature=data.get("synthesis_temperature", 0.3),
            retrieve_per_step=data.get("retrieve_per_step", True),
        )


# Planning prompt
PLANNING_PROMPT = """Break down the following complex question into smaller, logical sub-questions that can be answered step by step.

Question: {query}

Create a plan with {max_steps} or fewer sub-questions. Each sub-question should:
1. Be self-contained and answerable
2. Build on previous answers
3. Lead toward answering the main question

Provide the sub-questions as a numbered list:
1.
2.
3."""

# Step execution prompt
STEP_EXECUTION_PROMPT = """Answer the following sub-question based on the retrieved context.

Sub-question: {sub_question}

Retrieved Context:
{context}

Previous Answers:
{previous_answers}

Provide a clear, concise answer to this sub-question:"""

# Synthesis prompt
SYNTHESIS_PROMPT = """Synthesize the following step-by-step results into a comprehensive final answer.

Original Question: {query}

Step-by-Step Results:
{step_results}

Provide a coherent, well-structured answer that addresses the original question based on the accumulated knowledge:"""


class PlanSolveAgent(BaseAgent):
    """
    Plan-Solve agent for complex multi-step questions.

    Flow: Query → Plan Steps → Execute Each → Synthesize → Answer

    This agent handles complex questions by:
    1. Breaking the question into sub-questions (planning)
    2. Executing each sub-question with retrieval
    3. Synthesizing all results into a final answer
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: PromptManager | None = None,
        config: PlanSolveConfig | None = None,
    ):
        """
        Initialize Plan-Solve agent.

        Args:
            retriever: Retriever for fetching documents
            llm: Language model for planning and generation
            prompt_manager: Prompt manager for templates
            config: Plan-Solve configuration
        """
        super().__init__(config or PlanSolveConfig())
        self._agent_name = "plan_solve"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.plansolve_config = config or PlanSolveConfig()

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

        graph = StateGraph(PlanSolveState)

        # Add nodes
        graph.add_node("plan", self._plan_node)
        graph.add_node("execute_step", self._execute_step_node)
        graph.add_node("synthesize", self._synthesize_node)

        # Set entry point
        graph.set_entry_point("plan")

        # Add edges
        graph.add_edge("plan", "execute_step")

        # Conditional edge from execute_step
        graph.add_conditional_edges(
            "execute_step",
            self._has_more_steps,
            {"yes": "execute_step", "no": "synthesize"},
        )

        graph.add_edge("synthesize", END)

        return graph.compile()

    def _has_more_steps(self, state: PlanSolveState) -> str:
        """Check if there are more steps to execute."""
        current_step = state.get("current_step", 0)
        plan = state.get("plan", [])

        if current_step < len(plan):
            return "yes"
        return "no"

    async def _plan_node(self, state: PlanSolveState) -> PlanSolveState:
        """Create a plan of sub-questions."""
        start_time = time.time()

        query = state["query"]
        max_steps = state.get("max_steps", self.plansolve_config.max_steps)

        try:
            # Generate plan using LLM
            prompt = PLANNING_PROMPT.format(
                query=query,
                max_steps=max_steps,
            )

            messages = [Message.user(prompt)]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.plansolve_config.plan_temperature,
                max_tokens=500,
            )

            # Parse plan
            plan = self._parse_plan(response.content, max_steps)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.REWRITE,
                name="create_plan",
                input={"query": query, "max_steps": max_steps},
                output={
                    "plan": plan,
                    "num_steps": len(plan),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "plan": plan,
                "current_step": 0,
                "step_results": [],
                "step_contexts": [],
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Fallback: treat original question as single step
            step = AgentStep(
                step_type=StepType.ERROR,
                name="plan_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "plan": [query],  # Single-step fallback
                "current_step": 0,
                "step_results": [],
                "step_contexts": [],
                "steps": steps,
                "error": str(e),
            }

    def _parse_plan(self, response: str, max_steps: int) -> list[str]:
        """Parse plan from LLM response."""
        plan = []

        # Look for numbered lines
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            # Remove numbering (1., 1), etc.)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            line = re.sub(r"^[-•]\s*", "", line)
            line = line.strip("\"'")

            if line and len(line) > 10:  # Minimum length for valid step
                plan.append(line)

            if len(plan) >= max_steps:
                break

        # If no plan parsed, fallback to single step
        if not plan:
            plan = ["Answer the question directly"]

        return plan[:max_steps]

    async def _execute_step_node(self, state: PlanSolveState) -> PlanSolveState:
        """Execute the current step."""
        start_time = time.time()

        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        config_id = state["config_id"]
        step_results = list(state.get("step_results", []))
        step_contexts = list(state.get("step_contexts", []))

        if current_step >= len(plan):
            return state

        sub_question = plan[current_step]

        try:
            # Retrieve context for this step if enabled
            context_chunks = []
            context_str = ""

            if self.plansolve_config.retrieve_per_step:
                # Build query using sub-question + previous results
                step_query = sub_question
                if step_results:
                    step_query = (
                        f"{sub_question} Context: {' '.join(step_results[-2:])}"
                    )

                context_chunks = await self.retriever.retrieve(
                    query=step_query,
                    config_id=config_id,
                    top_k=self.plansolve_config.top_k_per_step,
                )

                # Filter by min score
                if self.config.min_score > 0:
                    context_chunks = [
                        c for c in context_chunks if c.score >= self.config.min_score
                    ]

                context_str = self.prompt_manager.format_context(
                    [c.to_dict() for c in context_chunks],
                    format_type="numbered",
                )

            # Build previous answers string
            previous_answers = ""
            if step_results:
                previous_answers = "\n".join(
                    [f"Step {i+1}: {result}" for i, result in enumerate(step_results)]
                )

            # Generate answer for this step
            prompt = STEP_EXECUTION_PROMPT.format(
                sub_question=sub_question,
                context=context_str or "No additional context retrieved.",
                previous_answers=previous_answers or "None",
            )

            messages = [
                Message.system(self.prompt_manager.get_system_prompt()),
                Message.user(prompt),
            ]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.plansolve_config.step_temperature,
                max_tokens=self.config.max_tokens,
            )

            step_answer = response.content.strip()

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.GENERATE,
                name=f"execute_step_{current_step + 1}",
                input={
                    "sub_question": sub_question,
                    "has_context": bool(context_chunks),
                },
                output={
                    "answer_length": len(step_answer),
                    "context_chunks": len(context_chunks),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            # Store results
            step_results.append(step_answer)
            step_contexts.append(context_chunks)

            return {
                **state,
                "step_results": step_results,
                "step_contexts": step_contexts,
                "current_step": current_step + 1,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            step = AgentStep(
                step_type=StepType.ERROR,
                name=f"step_{current_step + 1}_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)

            # Store error as result to continue
            step_results.append(f"Error: {str(e)}")
            step_contexts.append([])

            return {
                **state,
                "step_results": step_results,
                "step_contexts": step_contexts,
                "current_step": current_step + 1,
                "steps": steps,
                "error": str(e),
            }

    async def _synthesize_node(self, state: PlanSolveState) -> PlanSolveState:
        """Synthesize all step results into final answer."""
        start_time = time.time()

        query = state["query"]
        plan = state.get("plan", [])
        step_results = state.get("step_results", [])
        step_contexts = state.get("step_contexts", [])

        try:
            # Build step results string
            step_results_str = ""
            for i, (sub_q, result) in enumerate(zip(plan, step_results)):
                step_results_str += f"\nStep {i+1}: {sub_q}\nAnswer: {result}\n"

            # Synthesize using LLM
            prompt = SYNTHESIS_PROMPT.format(
                query=query,
                step_results=step_results_str,
            )

            messages = [
                Message.system(self.prompt_manager.get_system_prompt()),
                Message.user(prompt),
            ]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.plansolve_config.synthesis_temperature,
                max_tokens=self.config.max_tokens,
            )

            final_answer = response.content.strip()

            # Collect all unique sources
            all_sources = []
            seen_ids = set()
            for contexts in step_contexts:
                for chunk in contexts:
                    if chunk.chunk_id not in seen_ids:
                        seen_ids.add(chunk.chunk_id)
                        all_sources.append(chunk)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.GENERATE,
                name="synthesize_answer",
                input={
                    "num_steps": len(plan),
                    "num_sources": len(all_sources),
                },
                output={
                    "answer_length": len(final_answer),
                    "model": response.model,
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "final_answer": final_answer,
                "sources": all_sources,
                "steps": steps,
                "metadata": {
                    "model": response.model,
                    "usage": response.usage.to_dict() if response.usage else None,
                    "num_steps_executed": len(step_results),
                },
            }

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback: concatenate step results
            fallback_answer = "\n\n".join(
                [f"Step {i+1}: {result}" for i, result in enumerate(step_results)]
            )

            step = AgentStep(
                step_type=StepType.ERROR,
                name="synthesis_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "final_answer": fallback_answer,
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
        Run the Plan-Solve agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with synthesized answer
        """
        start_time = time.time()

        # Initial state
        initial_state: PlanSolveState = {
            "query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "plan": [],
            "current_step": 0,
            "max_steps": self.plansolve_config.max_steps,
            "step_results": [],
            "step_contexts": [],
            "synthesized_answer": "",
            "final_answer": "",
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
            metadata = {
                "plan": final_state.get("plan", []),
                "num_steps": len(final_state.get("plan", [])),
                "steps_executed": len(final_state.get("step_results", [])),
                **final_state.get("metadata", {}),
            }

            response = AgentResponse(
                answer=final_state.get("final_answer", ""),
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
            logger.error(f"Plan-Solve agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: PlanSolveState) -> PlanSolveState:
        """Execute Plan-Solve flow without LangGraph."""
        # Plan
        state = await self._plan_node(state)

        # Execute all steps
        while state.get("current_step", 0) < len(state.get("plan", [])):
            state = await self._execute_step_node(state)

        # Synthesize
        state = await self._synthesize_node(state)

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

        Note: Plan-Solve agent streams the final synthesized answer.
        """
        # Run the plan-solve flow first
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
