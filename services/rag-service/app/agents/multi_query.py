"""Multi-Query agent implementation using LangGraph."""

import logging
import time
from dataclasses import dataclass, field
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


class MultiQueryState(TypedDict, total=False):
    """State for Multi-Query agent execution."""

    # Input
    original_query: str
    config_id: str
    conversation_history: List[Dict[str, str]]

    # Query expansion
    expanded_queries: List[str]
    num_variations: int

    # Retrieval results
    all_results: Dict[str, List[RetrievedChunk]]  # query -> chunks
    merged_context: List[RetrievedChunk]

    # Generation
    answer: str
    sources: List[RetrievedChunk]

    # Tracking
    steps: List[AgentStep]
    error: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class MultiQueryConfig(AgentConfig):
    """Configuration specific to Multi-Query agent."""

    # Query expansion settings
    num_variations: int = 3
    expansion_temperature: float = 0.7

    # Retrieval settings
    top_k_per_query: int = 5
    max_total_chunks: int = 15

    # Fusion settings
    use_rrf: bool = True  # Use Reciprocal Rank Fusion
    rrf_k: int = 60

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiQueryConfig":
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
            num_variations=data.get("num_variations", 3),
            expansion_temperature=data.get("expansion_temperature", 0.7),
            top_k_per_query=data.get("top_k_per_query", 5),
            max_total_chunks=data.get("max_total_chunks", 15),
            use_rrf=data.get("use_rrf", True),
            rrf_k=data.get("rrf_k", 60),
        )


# Query expansion prompt
QUERY_EXPANSION_PROMPT = """Given the following question, generate {num_variations} alternative phrasings or perspectives that capture the same information need.

Original Question: {query}

Generate variations that:
1. Use different but related terminology
2. Rephrase from different angles
3. Include key concepts and synonyms

Provide exactly {num_variations} alternative questions, one per line:
1.
2.
3."""


class MultiQueryAgent(BaseAgent):
    """
    Multi-Query RAG agent with query expansion.

    Flow:
    Query → Generate Variations → Retrieve for Each → Merge Results (RRF) → Generate

    This agent improves retrieval coverage by:
    1. Expanding the original query into multiple variations
    2. Retrieving chunks for each variation
    3. Merging results using Reciprocal Rank Fusion
    4. Generating answer from diverse context
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: Optional[PromptManager] = None,
        config: Optional[MultiQueryConfig] = None,
    ):
        """
        Initialize Multi-Query agent.

        Args:
            retriever: Retriever for fetching documents
            llm: Language model for query expansion and generation
            prompt_manager: Prompt manager for templates
            config: Multi-Query configuration
        """
        super().__init__(config or MultiQueryConfig())
        self._agent_name = "multi_query"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.multiquery_config = config or MultiQueryConfig()

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

        graph = StateGraph(MultiQueryState)

        # Add nodes
        graph.add_node("expand", self._expand_query_node)
        graph.add_node("retrieve_all", self._retrieve_all_node)
        graph.add_node("merge", self._merge_results_node)
        graph.add_node("generate", self._generate_node)

        # Set entry point
        graph.set_entry_point("expand")

        # Linear flow
        graph.add_edge("expand", "retrieve_all")
        graph.add_edge("retrieve_all", "merge")
        graph.add_edge("merge", "generate")
        graph.add_edge("generate", END)

        return graph.compile()

    async def _expand_query_node(self, state: MultiQueryState) -> MultiQueryState:
        """Expand original query into multiple variations."""
        start_time = time.time()

        query = state["original_query"]
        num_variations = state.get("num_variations", self.multiquery_config.num_variations)

        try:
            # Generate query variations
            prompt = QUERY_EXPANSION_PROMPT.format(
                query=query,
                num_variations=num_variations,
            )

            messages = [Message.user(prompt)]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.multiquery_config.expansion_temperature,
                max_tokens=300,
            )

            # Parse expanded queries
            expanded = self._parse_expanded_queries(response.content, num_variations)

            # Always include original query
            all_queries = [query] + expanded

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.REWRITE,
                name="expand_query",
                input={"original_query": query, "num_variations": num_variations},
                output={
                    "expanded_queries": expanded,
                    "total_queries": len(all_queries),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "expanded_queries": all_queries,
                "num_variations": len(all_queries),
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            # Fallback to original query only
            step = AgentStep(
                step_type=StepType.ERROR,
                name="expand_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "expanded_queries": [query],
                "num_variations": 1,
                "steps": steps,
                "error": str(e),
            }

    def _parse_expanded_queries(self, response: str, expected_count: int) -> List[str]:
        """Parse expanded queries from LLM response."""
        queries = []

        # Try to find numbered lines
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            # Remove common prefixes
            for prefix in ["1.", "2.", "3.", "4.", "5.", "-", "•"]:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break

            # Clean up quotes
            line = line.strip('"\'')

            if line and len(line) > 10:  # Minimum length for a valid query
                queries.append(line)

            if len(queries) >= expected_count:
                break

        return queries[:expected_count]

    async def _retrieve_all_node(self, state: MultiQueryState) -> MultiQueryState:
        """Retrieve chunks for all query variations."""
        start_time = time.time()

        queries = state.get("expanded_queries", [state["original_query"]])
        config_id = state["config_id"]
        top_k = state.get("top_k_per_query", self.multiquery_config.top_k_per_query)

        try:
            # Retrieve for each query in parallel
            import asyncio

            async def retrieve_for_query(query: str) -> tuple[str, List[RetrievedChunk]]:
                try:
                    chunks = await self.retriever.retrieve(
                        query=query,
                        config_id=config_id,
                        top_k=top_k,
                    )
                    return query, chunks
                except Exception as e:
                    logger.error(f"Retrieval failed for query '{query}': {e}")
                    return query, []

            # Run retrievals concurrently
            tasks = [retrieve_for_query(q) for q in queries]
            results = await asyncio.gather(*tasks)

            # Collect results
            all_results: Dict[str, List[RetrievedChunk]] = {}
            total_chunks = 0

            for query, chunks in results:
                all_results[query] = chunks
                total_chunks += len(chunks)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.RETRIEVE,
                name="retrieve_all_queries",
                input={"queries": queries, "top_k": top_k},
                output={
                    "total_chunks": total_chunks,
                    "chunks_per_query": {q: len(c) for q, c in all_results.items()},
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "all_results": all_results,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Multi-query retrieval failed: {e}")
            return {
                **state,
                "all_results": {},
                "error": str(e),
            }

    async def _merge_results_node(self, state: MultiQueryState) -> MultiQueryState:
        """Merge retrieval results using RRF."""
        start_time = time.time()

        all_results = state.get("all_results", {})
        max_total = state.get("max_total_chunks", self.multiquery_config.max_total_chunks)

        try:
            if self.multiquery_config.use_rrf:
                merged = self._rrf_merge(all_results, max_total)
            else:
                # Simple deduplication and score-based merge
                merged = self._simple_merge(all_results, max_total)

            # Format context
            context = self.prompt_manager.format_context(
                [c.to_dict() for c in merged],
                format_type="numbered",
            )

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.REWRITE,
                name="merge_results",
                input={"total_input_chunks": sum(len(c) for c in all_results.values())},
                output={
                    "merged_chunks": len(merged),
                    "unique_sources": len(set(c.chunk_id for c in merged)),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "merged_context": merged,
                "context": context,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Result merging failed: {e}")
            # Fallback: use chunks from original query only
            original_query = state["original_query"]
            fallback_chunks = all_results.get(original_query, [])

            return {
                **state,
                "merged_context": fallback_chunks,
                "error": str(e),
            }

    def _rrf_merge(
        self,
        all_results: Dict[str, List[RetrievedChunk]],
        max_total: int,
    ) -> List[RetrievedChunk]:
        """Merge results using Reciprocal Rank Fusion."""
        from collections import defaultdict

        k = self.multiquery_config.rrf_k
        rrf_scores: Dict[str, float] = defaultdict(float)
        chunks_by_id: Dict[str, RetrievedChunk] = {}

        # Calculate RRF scores
        for query, chunks in all_results.items():
            for rank, chunk in enumerate(chunks):
                chunk_id = chunk.chunk_id
                rrf_scores[chunk_id] += 1.0 / (k + rank + 1)

                # Keep chunk with highest original score
                if chunk_id not in chunks_by_id or chunk.score > chunks_by_id[chunk_id].score:
                    chunks_by_id[chunk_id] = chunk

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build result list
        merged = []
        for chunk_id in sorted_ids[:max_total]:
            chunk = chunks_by_id[chunk_id]
            # Update score with RRF score
            chunk.score = rrf_scores[chunk_id]
            merged.append(chunk)

        return merged

    def _simple_merge(
        self,
        all_results: Dict[str, List[RetrievedChunk]],
        max_total: int,
    ) -> List[RetrievedChunk]:
        """Simple merge with deduplication by chunk ID."""
        seen_ids = set()
        merged = []

        # Collect all chunks with their scores
        all_chunks = []
        for query, chunks in all_results.items():
            for chunk in chunks:
                all_chunks.append(chunk)

        # Sort by score descending
        all_chunks.sort(key=lambda x: x.score, reverse=True)

        # Deduplicate and limit
        for chunk in all_chunks:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                merged.append(chunk)

                if len(merged) >= max_total:
                    break

        return merged

    async def _generate_node(self, state: MultiQueryState) -> MultiQueryState:
        """Generate final answer from merged context."""
        start_time = time.time()

        original_query = state["original_query"]
        context = state.get("context", "")
        merged_chunks = state.get("merged_context", [])
        history = state.get("conversation_history", [])

        try:
            # Get system prompt
            system_prompt = self.prompt_manager.get_system_prompt(
                name=self.config.system_prompt_name
            )

            # Get RAG prompt
            history_str = self.prompt_manager.format_history(history) if history else ""
            rag_prompt = self.prompt_manager.get_rag_prompt(
                context=context,
                query=original_query,
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
                input={
                    "query": original_query,
                    "context_length": len(context),
                    "num_sources": len(merged_chunks),
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
                "sources": merged_chunks,
                "steps": steps,
                "metadata": {
                    "model": response.model,
                    "usage": response.usage.to_dict() if response.usage else None,
                },
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                **state,
                "answer": "I apologize, but I encountered an error generating a response.",
                "error": str(e),
            }

    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the Multi-Query agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and query expansion info
        """
        start_time = time.time()

        # Initial state
        initial_state: MultiQueryState = {
            "original_query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "expanded_queries": [],
            "num_variations": self.multiquery_config.num_variations,
            "all_results": {},
            "merged_context": [],
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
            metadata = {
                "expanded_queries": final_state.get("expanded_queries", []),
                "num_variations": final_state.get("num_variations", 1),
                "total_chunks_before_merge": sum(
                    len(c) for c in final_state.get("all_results", {}).values()
                ),
                "chunks_after_merge": len(final_state.get("merged_context", [])),
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
            logger.error(f"Multi-Query agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: MultiQueryState) -> MultiQueryState:
        """Execute Multi-Query flow without LangGraph."""
        # Expand query
        state = await self._expand_query_node(state)

        # Retrieve for all queries
        state = await self._retrieve_all_node(state)

        # Merge results
        state = await self._merge_results_node(state)

        # Generate answer
        state = await self._generate_node(state)

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

        Note: Multi-Query agent streams the final answer generation.
        """
        # Run the multi-query flow first
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
