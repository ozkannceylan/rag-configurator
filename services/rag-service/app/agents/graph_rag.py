"""GraphRAG agent: uses community summaries for global questions."""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

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
from app.retrieval.base import BaseRetriever

logger = logging.getLogger(__name__)


CLASSIFY_PROMPT = """Classify the following user query as either "global" or "local".

A "global" query asks for broad summaries, overviews, themes, or trends across many documents.
A "local" query asks about a specific fact, entity, event, or detail.

Query: {query}

Answer with exactly one word: global or local"""


GLOBAL_SYNTHESIZE_PROMPT = """You are answering a broad question using community summaries from a knowledge graph.

Community Summaries:
{summaries}

Question: {query}

Provide a comprehensive answer that synthesizes information across the community summaries. If the summaries do not contain relevant information, say so.

Answer:"""


@dataclass
class GraphRAGConfig(AgentConfig):
    """Configuration specific to GraphRAG agent."""

    # Number of community summaries to retrieve for global queries
    max_community_summaries: int = 10

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphRAGConfig":
        """Create from dictionary."""
        return cls(
            top_k=data.get("top_k", 5),
            min_score=data.get("min_score", 0.0),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2048),
            streaming=data.get("streaming", False),
            system_prompt_name=data.get("system_prompt_name", "default"),
            rag_prompt_name=data.get("rag_prompt_name", "default"),
            include_steps=data.get("include_steps", True),
            verbose=data.get("verbose", False),
            timeout_seconds=data.get("timeout_seconds", 60.0),
            max_community_summaries=data.get("max_community_summaries", 10),
        )


class GraphRAGAgent(BaseAgent):
    """
    Microsoft GraphRAG: uses community summaries for global questions.

    For "global" queries (broad, summary-type): retrieve community summaries
    and synthesize an answer from them.
    For "local" queries: use standard vector retrieval on chunks.
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: PromptManager | None = None,
        config: GraphRAGConfig | None = None,
        db: Any | None = None,
    ):
        """
        Initialize GraphRAG agent.

        Args:
            retriever: Retriever for local queries (vector search).
            llm: Language model for generation and classification.
            prompt_manager: Prompt manager for templates.
            config: Agent configuration.
            db: MongoDB database for reading community summaries.
        """
        super().__init__(config or GraphRAGConfig())
        self._agent_name = "graph_rag"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.db = db

    async def _classify_query(self, query: str) -> str:
        """
        Classify query as global or local using LLM.

        Returns:
            "global" or "local"
        """
        prompt = CLASSIFY_PROMPT.replace("{query}", query)
        messages = [Message.user(prompt)]

        response = await self.llm.generate(
            messages=messages,
            temperature=0.0,
            max_tokens=10,
        )
        classification = response.content.strip().lower()

        if "global" in classification:
            return "global"
        return "local"

    async def _retrieve_community_summaries(
        self, config_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retrieve community summaries from MongoDB."""
        if self.db is None:
            return []

        collection = self.db["community_summaries"]
        cursor = (
            collection.find(
                {"config_id": config_id},
                {"summary": 1, "entities": 1, "community_id": 1, "level": 1},
            )
            .sort("level", -1)
            .limit(limit)
        )

        summaries = []
        async for doc in cursor:
            summaries.append(doc)
        return summaries

    async def _global_answer(
        self,
        query: str,
        config_id: str,
        steps: list[AgentStep],
    ) -> dict[str, Any]:
        """Generate answer from community summaries (global path)."""
        start = time.time()

        max_summaries = (
            self.config.max_community_summaries
            if isinstance(self.config, GraphRAGConfig)
            else 10
        )
        summaries = await self._retrieve_community_summaries(
            config_id, limit=max_summaries
        )

        retrieve_duration = (time.time() - start) * 1000
        steps.append(
            AgentStep(
                step_type=StepType.RETRIEVE,
                name="retrieve_community_summaries",
                input={"config_id": config_id, "limit": max_summaries},
                output={"summary_count": len(summaries)},
                duration_ms=retrieve_duration,
            )
        )

        if not summaries:
            return {
                "answer": "No community summaries are available for this configuration. "
                "Please run the GraphRAG indexing pipeline first.",
                "sources": [],
            }

        # Format summaries for prompt
        summary_texts = []
        for i, s in enumerate(summaries, 1):
            entities = ", ".join(s.get("entities", [])[:5])
            summary_texts.append(
                f"[Community {i}] (Entities: {entities})\n{s.get('summary', '')}"
            )
        summaries_block = "\n\n".join(summary_texts)

        # Generate answer
        gen_start = time.time()
        prompt = GLOBAL_SYNTHESIZE_PROMPT.replace(
            "{summaries}", summaries_block
        ).replace("{query}", query)

        system_prompt = self.prompt_manager.get_system_prompt(
            name=self.config.system_prompt_name
        )

        messages = [
            Message.system(system_prompt),
            Message.user(prompt),
        ]

        response = await self.llm.generate(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        gen_duration = (time.time() - gen_start) * 1000
        steps.append(
            AgentStep(
                step_type=StepType.GENERATE,
                name="global_synthesis",
                input={"summary_count": len(summaries)},
                output={
                    "answer_length": len(response.content),
                    "model": response.model,
                },
                duration_ms=gen_duration,
            )
        )

        return {"answer": response.content, "sources": []}

    async def _local_answer(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None,
        steps: list[AgentStep],
    ) -> dict[str, Any]:
        """Generate answer from vector-retrieved chunks (local path)."""
        # Retrieve
        start = time.time()
        chunks = await self.retriever.retrieve(
            query=query,
            config_id=config_id,
            top_k=self.config.top_k,
        )

        if self.config.min_score > 0:
            chunks = [c for c in chunks if c.score >= self.config.min_score]

        context = self.prompt_manager.format_context(
            [c.to_dict() for c in chunks],
            format_type="numbered",
        )

        retrieve_duration = (time.time() - start) * 1000
        steps.append(
            AgentStep(
                step_type=StepType.RETRIEVE,
                name="retrieve_chunks",
                input={"query": query, "top_k": self.config.top_k},
                output={"chunk_count": len(chunks)},
                duration_ms=retrieve_duration,
            )
        )

        # Generate
        gen_start = time.time()
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

        messages = [
            Message.system(system_prompt),
            Message.user(rag_prompt),
        ]

        response = await self.llm.generate(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        gen_duration = (time.time() - gen_start) * 1000
        steps.append(
            AgentStep(
                step_type=StepType.GENERATE,
                name="local_generate",
                input={"context_length": len(context), "query": query},
                output={
                    "answer_length": len(response.content),
                    "model": response.model,
                },
                duration_ms=gen_duration,
            )
        )

        return {"answer": response.content, "sources": chunks}

    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the GraphRAG agent.

        Classifies the query as global/local, then routes accordingly.
        """
        total_start = time.time()
        steps: list[AgentStep] = []

        try:
            # Step 1: Classify query
            classify_start = time.time()
            query_type = await self._classify_query(query)
            classify_duration = (time.time() - classify_start) * 1000

            steps.append(
                AgentStep(
                    step_type=StepType.ROUTE,
                    name="classify_query",
                    input={"query": query},
                    output={"query_type": query_type},
                    duration_ms=classify_duration,
                )
            )

            # Step 2: Route to appropriate path
            if query_type == "global":
                result = await self._global_answer(query, config_id, steps)
            else:
                result = await self._local_answer(
                    query, config_id, conversation_history, steps
                )

            total_duration = (time.time() - total_start) * 1000

            return AgentResponse(
                answer=result["answer"],
                sources=self._format_sources(result.get("sources", [])),
                steps=steps if self.config.include_steps else [],
                total_duration_ms=total_duration,
                metadata={"query_type": query_type, "agent": "graph_rag"},
            )

        except Exception as e:
            logger.error("GraphRAG agent execution failed: %s", e)
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def stream(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream the GraphRAG response.

        For simplicity, classifies the query first, then streams the generation.
        """
        query_type = await self._classify_query(query)

        if query_type == "global":
            # Retrieve community summaries
            max_summaries = (
                self.config.max_community_summaries
                if isinstance(self.config, GraphRAGConfig)
                else 10
            )
            summaries = await self._retrieve_community_summaries(
                config_id, limit=max_summaries
            )
            summary_texts = []
            for i, s in enumerate(summaries, 1):
                entities = ", ".join(s.get("entities", [])[:5])
                summary_texts.append(
                    f"[Community {i}] (Entities: {entities})\n{s.get('summary', '')}"
                )
            summaries_block = "\n\n".join(summary_texts)

            prompt = GLOBAL_SYNTHESIZE_PROMPT.replace(
                "{summaries}", summaries_block
            ).replace("{query}", query)
        else:
            # Local: retrieve chunks
            chunks = await self.retriever.retrieve(
                query=query,
                config_id=config_id,
                top_k=self.config.top_k,
            )
            if self.config.min_score > 0:
                chunks = [c for c in chunks if c.score >= self.config.min_score]

            context = self.prompt_manager.format_context(
                [c.to_dict() for c in chunks],
                format_type="numbered",
            )

            history_str = ""
            if conversation_history:
                history_str = self.prompt_manager.format_history(conversation_history)

            prompt = self.prompt_manager.get_rag_prompt(
                context=context,
                query=query,
                name=self.config.rag_prompt_name,
                history=history_str,
            )

        system_prompt = self.prompt_manager.get_system_prompt(
            name=self.config.system_prompt_name
        )

        messages = [
            Message.system(system_prompt),
            Message.user(prompt),
        ]

        async for chunk in self.llm.stream(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            yield chunk

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self.retriever, "close"):
            await self.retriever.close()
        if hasattr(self.llm, "close"):
            await self.llm.close()
