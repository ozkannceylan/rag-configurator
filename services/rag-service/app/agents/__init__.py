"""Agent module for RAG pipelines."""

from app.agents.base import (
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentState,
    AgentStep,
    BaseAgent,
    StepType,
)
from app.agents.crag import (
    CRAGAgent,
    CRAGConfig,
    CRAGState,
    RelevanceEvaluation,
    RelevanceGrade,
)
from app.agents.naive import NaiveRAGAgent
from app.agents.react import (
    Action,
    Observation,
    ReActAgent,
    ReActConfig,
    ReActState,
    Thought,
    Tool,
    ToolType,
)

__all__ = [
    # Base
    "BaseAgent",
    "AgentResponse",
    "AgentStep",
    "AgentState",
    "AgentConfig",
    "AgentError",
    "StepType",
    # Naive RAG
    "NaiveRAGAgent",
    # ReAct
    "ReActAgent",
    "ReActConfig",
    "ReActState",
    "Tool",
    "ToolType",
    "Thought",
    "Action",
    "Observation",
    # CRAG
    "CRAGAgent",
    "CRAGConfig",
    "CRAGState",
    "RelevanceGrade",
    "RelevanceEvaluation",
]
