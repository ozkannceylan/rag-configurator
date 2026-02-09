"""Naive RAG agent implementation using LangGraph."""

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.agents.base import (
    BaseAgent,
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentState,
    AgentStep,
    StepType,
)
from app.llm.base import BaseLLM, Message
from app.prompts.manager import PromptManager
from app.retrieval.base import BaseRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class NaiveRAGAgent(BaseAgent):
    """
    Simple retrieve-then-generate RAG agent.

    Flow: Query → Retrieve → Generate → Answer

    This is the simplest RAG implementation that:
    1. Retrieves relevant chunks based on the query
    2. Generates an answer using the retrieved context
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: Optional[PromptManager] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize Naive RAG agent.

        Args:
            retriever: Retriever for fetching relevant chunks
            llm: Language model for generation
            prompt_manager: Prompt manager for templates
            config: Agent configuration
        """
        super().__init__(config)
        self._agent_name = "naive_rag"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()

        # Build LangGraph if available, otherwise use simple flow
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

        # Create graph with AgentState
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("generate", self._generate_node)

        # Add edges
        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", END)

        # Compile
        return graph.compile()

    async def _retrieve_node(self, state: AgentState) -> AgentState:
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
                output={"chunk_count": len(chunks)},
                duration_ms=duration,
            )

            # Update state
            steps = state.get("steps", [])
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
            steps = state.get("steps", [])
            steps.append(step)
            return {
                **state,
                "retrieved_chunks": [],
                "context": "No context available.",
                "steps": steps,
                "error": str(e),
            }

    async def _generate_node(self, state: AgentState) -> AgentState:
        """Generate answer from context."""
        start_time = time.time()

        query = state["query"]
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

            # Build messages
            messages = [
                Message.system(system_prompt),
                Message.user(rag_prompt),
            ]

            # Generate response
            response = await self.llm.generate(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            duration = (time.time() - start_time) * 1000

            # Create step
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
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            )

            steps = state.get("steps", [])
            steps.append(step)

            return {
                **state,
                "answer": response.content,
                "sources": state.get("retrieved_chunks", []),
                "steps": steps,
                "metadata": {
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
            steps = state.get("steps", [])
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
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the naive RAG agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and sources
        """
        start_time = time.time()

        # Initial state
        initial_state: AgentState = {
            "query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "retrieved_chunks": [],
            "context": "",
            "answer": "",
            "sources": [],
            "steps": [],
            "metadata": {},
        }

        try:
            if self._use_langgraph and self._graph is not None:
                # Use LangGraph
                final_state = await self._graph.ainvoke(initial_state)
            else:
                # Use simple flow
                final_state = await self._simple_flow(initial_state)

            total_duration = (time.time() - start_time) * 1000

            # Build response
            response = AgentResponse(
                answer=final_state.get("answer", ""),
                sources=self._format_sources(final_state.get("sources", [])),
                steps=final_state.get("steps", []) if self.config.include_steps else [],
                total_duration_ms=total_duration,
                metadata=final_state.get("metadata", {}),
            )

            # Add token usage from metadata
            if final_state.get("metadata", {}).get("usage"):
                usage = final_state["metadata"]["usage"]
                response.prompt_tokens = usage.get("prompt_tokens", 0)
                response.completion_tokens = usage.get("completion_tokens", 0)
                response.total_tokens = usage.get("total_tokens", 0)

            return response

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: AgentState) -> AgentState:
        """Execute simple retrieve-then-generate flow without LangGraph."""
        # Retrieve
        state = await self._retrieve_node(state)

        # Generate
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

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Yields:
            String chunks of the response
        """
        # First, retrieve context
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

        # Get prompts
        system_prompt = self.prompt_manager.get_system_prompt(
            name=self.config.system_prompt_name
        )

        history_str = ""
        if conversation_history:
            history_str = self.prompt_manager.format_history(conversation_history)

        rag_prompt = self.prompt_manager.get_rag_prompt(
            context=context,
            query=query,
            name=self.config.rag_prompt_name,
            history=history_str,
        )

        # Build messages
        messages = [
            Message.system(system_prompt),
            Message.user(rag_prompt),
        ]

        # Stream response
        async for chunk in self.llm.stream(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            yield chunk

    async def run_with_sources(
        self,
        query: str,
        config_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs: Any,
    ) -> tuple[str, List[RetrievedChunk]]:
        """
        Run agent and return answer with sources separately.

        Convenience method for simpler access to results.

        Returns:
            Tuple of (answer, sources)
        """
        response = await self.run(
            query=query,
            config_id=config_id,
            conversation_history=conversation_history,
            **kwargs,
        )
        return response.answer, response.sources

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self.retriever, "close"):
            await self.retriever.close()
        if hasattr(self.llm, "close"):
            await self.llm.close()


class NaiveRAGAgentFactory:
    """Factory for creating Naive RAG agents."""

    @staticmethod
    async def create(
        db,
        llm_provider: str = "openai",
        retrieval_method: str = "vector",
        config: Optional[AgentConfig] = None,
        **kwargs: Any,
    ) -> NaiveRAGAgent:
        """
        Create a configured Naive RAG agent.

        Args:
            db: Database connection
            llm_provider: LLM provider name
            retrieval_method: Retrieval method name
            config: Agent configuration
            **kwargs: Additional configuration

        Returns:
            Configured NaiveRAGAgent
        """
        from app.llm.factory import get_llm, LLMProvider
        from app.retrieval.factory import get_retriever, RetrievalMethod

        # Create retriever
        try:
            method = RetrievalMethod(retrieval_method.lower())
        except ValueError:
            method = RetrievalMethod.VECTOR

        retriever = get_retriever(
            method=method,
            db=db,
            **kwargs.get("retriever_kwargs", {}),
        )

        # Create LLM
        try:
            provider = LLMProvider(llm_provider.lower())
        except ValueError:
            provider = LLMProvider.OPENAI

        llm = get_llm(
            provider=provider,
            **kwargs.get("llm_kwargs", {}),
        )

        # Create prompt manager
        prompt_manager = PromptManager()

        return NaiveRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=config,
        )
