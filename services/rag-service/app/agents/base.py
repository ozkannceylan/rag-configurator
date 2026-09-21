"""Base agent interface and common types."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypedDict

from app.retrieval.base import RetrievedChunk

logger = logging.getLogger(__name__)


class StepType(StrEnum):
    """Types of agent steps."""

    RETRIEVE = "retrieve"
    GENERATE = "generate"
    REWRITE = "rewrite"
    ROUTE = "route"
    EVALUATE = "evaluate"
    REFINE = "refine"
    TOOL_CALL = "tool_call"
    ERROR = "error"


@dataclass
class AgentStep:
    """A single step in agent execution."""

    step_type: StepType
    name: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    duration_ms: float = 0.0
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_type": self.step_type.value,
            "name": self.name,
            "input": self.input,
            "output": self.output,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AgentResponse:
    """Response from agent execution."""

    answer: str
    sources: list[RetrievedChunk] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Token usage tracking
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_ms": self.total_duration_ms,
            "metadata": self.metadata,
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
            },
        }

    @property
    def source_count(self) -> int:
        """Get number of sources."""
        return len(self.sources)

    @property
    def step_count(self) -> int:
        """Get number of steps."""
        return len(self.steps)


class AgentState(TypedDict, total=False):
    """State for LangGraph agent execution."""

    # Input
    query: str
    config_id: str
    conversation_history: list[dict[str, str]]

    # Retrieval
    retrieved_chunks: list[RetrievedChunk]
    context: str

    # Generation
    answer: str
    sources: list[RetrievedChunk]

    # Tracking
    steps: list[AgentStep]
    error: str | None

    # Metadata
    metadata: dict[str, Any]


@dataclass
class AgentConfig:
    """Configuration for agents."""

    # Retrieval settings
    top_k: int = 5
    min_score: float = 0.0

    # Generation settings
    temperature: float = 0.7
    max_tokens: int = 2048
    streaming: bool = False

    # Prompt settings
    system_prompt_name: str = "default"
    rag_prompt_name: str = "default"

    # Debug settings
    include_steps: bool = True
    verbose: bool = False

    # Timeout
    timeout_seconds: float = 60.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
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
        )


class AgentError(Exception):
    """Error during agent execution."""

    def __init__(
        self,
        message: str,
        step: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.step = step
        self.details = details or {}
        super().__init__(f"[{step}] {message}" if step else message)


class BaseAgent(ABC):
    """Abstract base class for RAG agents."""

    def __init__(
        self,
        config: AgentConfig | None = None,
    ):
        """
        Initialize base agent.

        Args:
            config: Agent configuration
        """
        self.config = config or AgentConfig()
        self._agent_name = "base"

    @property
    def name(self) -> str:
        """Get agent name."""
        return self._agent_name

    @abstractmethod
    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the agent on a query.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and metadata
        """
        pass

    @abstractmethod
    async def stream(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
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
        pass

    async def close(self) -> None:
        """Clean up resources."""
        pass

    def _create_step(
        self,
        step_type: StepType,
        name: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        **metadata: Any,
    ) -> AgentStep:
        """Create an agent step for tracking."""
        return AgentStep(
            step_type=step_type,
            name=name,
            input=input_data,
            output=output_data,
            duration_ms=duration_ms,
            metadata=metadata,
        )

    def _format_sources(
        self,
        chunks: list[RetrievedChunk],
        max_sources: int = 10,
    ) -> list[RetrievedChunk]:
        """Format and limit sources."""
        # Sort by score descending
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        return sorted_chunks[:max_sources]
