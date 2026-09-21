"""Agent factory for creating agent instances."""

import logging
from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.crag import CRAGAgent, CRAGConfig
from app.agents.graph_rag import GraphRAGAgent, GraphRAGConfig
from app.agents.multi_query import MultiQueryAgent, MultiQueryConfig
from app.agents.naive import NaiveRAGAgent
from app.agents.plan_solve import PlanSolveAgent, PlanSolveConfig
from app.agents.react import ReActAgent, ReActConfig
from app.agents.self_rag import SelfRAGAgent, SelfRAGConfig
from app.llm.base import BaseLLM
from app.prompts.manager import PromptManager
from app.retrieval.base import BaseRetriever

logger = logging.getLogger(__name__)


def create_agent(
    agent_type: str,
    retriever: BaseRetriever,
    llm: BaseLLM,
    prompt_manager: PromptManager | None = None,
    config: dict[str, Any] | None = None,
) -> BaseAgent:
    """
    Create an agent instance based on type.

    Args:
        agent_type: Type of agent to create
        retriever: Retriever instance
        llm: LLM instance
        prompt_manager: Prompt manager instance
        config: Agent configuration dict

    Returns:
        Configured agent instance
    """
    config = config or {}
    prompt_manager = prompt_manager or PromptManager()

    agent_type_lower = agent_type.lower()

    if agent_type_lower in ["naive", "naive_rag", "simple", "default"]:
        agent_config = AgentConfig.from_dict(config)
        return NaiveRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=agent_config,
        )

    elif agent_type_lower == "react":
        react_config = ReActConfig.from_dict(config)
        return ReActAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=react_config,
        )

    elif agent_type_lower in ["crag", "corrective"]:
        crag_config = CRAGConfig.from_dict(config)
        return CRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=crag_config,
        )

    elif agent_type_lower in ["self_rag", "selfrag", "reflective"]:
        selfrag_config = SelfRAGConfig.from_dict(config)
        return SelfRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=selfrag_config,
        )

    elif agent_type_lower in ["multi_query", "multiquery", "expand"]:
        multi_config = MultiQueryConfig.from_dict(config)
        return MultiQueryAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=multi_config,
        )

    elif agent_type_lower in ["plan_solve", "plansolve", "plan-solve"]:
        plan_config = PlanSolveConfig.from_dict(config)
        return PlanSolveAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=plan_config,
        )

    elif agent_type_lower in ["graph_rag", "graphrag", "graph-rag"]:
        graph_config = GraphRAGConfig.from_dict(config)
        return GraphRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=graph_config,
        )

    else:
        logger.warning(f"Unknown agent type '{agent_type}', using naive")
        agent_config = AgentConfig.from_dict(config)
        return NaiveRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=agent_config,
        )


def list_available_agents() -> dict[str, dict[str, Any]]:
    """
    List all available agent types.

    Returns:
        Dictionary of agent type -> description
    """
    return {
        "naive": {
            "name": "Naive RAG",
            "description": "Simple retrieve-then-generate RAG agent",
            "use_case": "Basic Q&A with retrieved context",
        },
        "react": {
            "name": "ReAct",
            "description": "Reasoning and Acting agent with tool use",
            "use_case": "Multi-step reasoning with iterative retrieval",
        },
        "crag": {
            "name": "CRAG",
            "description": "Corrective RAG with self-evaluation",
            "use_case": "Self-correcting retrieval with relevance evaluation",
        },
        "self_rag": {
            "name": "Self-RAG",
            "description": "Self-reflective RAG with critique",
            "use_case": "Questions requiring self-verification",
        },
        "multi_query": {
            "name": "Multi-Query",
            "description": "Query expansion for better coverage",
            "use_case": "Complex questions needing multiple perspectives",
        },
        "plan_solve": {
            "name": "Plan-Solve",
            "description": "Planning-based agent for complex questions",
            "use_case": "Multi-step questions requiring decomposition",
        },
        "graph_rag": {
            "name": "GraphRAG",
            "description": "Microsoft GraphRAG with community summaries for global questions",
            "use_case": "Broad overview questions across large document collections",
        },
    }


# Alias for backward compatibility
get_agent = create_agent
