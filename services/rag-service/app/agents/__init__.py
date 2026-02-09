"""Agent module for RAG pipelines."""

from app.agents.base import (
    BaseAgent,
    AgentResponse,
    AgentStep,
    AgentState,
    AgentConfig,
    AgentError,
    StepType,
)
from app.agents.naive import NaiveRAGAgent
from app.agents.react import (
    ReActAgent,
    ReActConfig,
    ReActState,
    Tool,
    ToolType,
    Thought,
    Action,
    Observation,
)
from app.agents.crag import (
    CRAGAgent,
    CRAGConfig,
    CRAGState,
    RelevanceGrade,
    RelevanceEvaluation,
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
