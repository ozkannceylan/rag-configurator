"""API endpoints for RAG queries."""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.agents.base import AgentResponse
from app.core.auth import get_authenticated_user_id, require_config_access
from app.core.query_cache import query_cache
from app.db.mongodb import mongodb
from app.llm.base import LLMContextLengthError, LLMError
from app.llm.factory import LLMProvider, get_llm
from app.prompts.manager import PromptManager
from app.retrieval.factory import get_retriever_from_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request model for query endpoint."""

    query: str = Field(..., description="User query text", max_length=10000)
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    user_role: Optional[str] = Field(None, description="User role for RBAC")
    include_sources: bool = Field(True, description="Include source chunks in response")
    include_debug: bool = Field(False, description="Include debug information")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation messages"
    )


class SourceResponse(BaseModel):
    """Source chunk in response."""

    content: str
    score: float
    metadata: Dict[str, Any]
    source_type: str


class QueryResponse(BaseModel):
    """Response model for query endpoint."""

    answer: str
    sources: List[SourceResponse]
    debug: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]


class DebugInfo(BaseModel):
    """Debug information for query execution."""

    steps: List[Dict[str, Any]]
    retrieval_time_ms: int
    generation_time_ms: int
    total_time_ms: int


@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest, http_request: Request):
    """
    Execute a single RAG query.

    This endpoint processes a query through the RAG pipeline:
    1. Retrieves relevant chunks based on configuration
    2. Generates an answer using the configured LLM
    3. Returns the answer with source citations
    """
    start_time = time.time()

    try:
        # Get database connection
        db = mongodb.get_database()

        user_id = get_authenticated_user_id(http_request)
        config_doc = await require_config_access(db, request.config_id, user_id)

        # Build pipeline config from actual config structure
        from app.api.v1.stream import build_pipeline_config
        pipeline_config = build_pipeline_config(config_doc)

        # Check query cache if caching is enabled
        cache_config = config_doc.get("cache", {})
        cache_enabled = cache_config.get("enabled", False)
        query_cache_ttl = cache_config.get("query_cache_ttl", 300)

        if cache_enabled:
            cached = await query_cache.get(request.config_id, request.query)
            if cached is not None:
                total_time = int((time.time() - start_time) * 1000)
                cached_metadata = cached.get("metadata", {})
                cached_metadata["cache_hit"] = True
                cached_metadata["total_duration_ms"] = total_time
                return QueryResponse(
                    answer=cached.get("answer", ""),
                    sources=[
                        SourceResponse(**s) for s in cached.get("sources", [])
                    ],
                    debug=cached.get("debug"),
                    metadata=cached_metadata,
                )

        # Create retriever
        retriever = get_retriever_from_config(
            db=db,
            pipeline_config=pipeline_config,
        )

        # Create LLM
        llm = get_llm_from_config(pipeline_config)

        # Create prompt manager
        prompt_manager = PromptManager()

        # Get agent type from config
        agent_config = pipeline_config.get("agent", {})
        agent_type = agent_config.get("type", "naive")

        # Create agent
        agent = get_agent(
            agent_type=agent_type,
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=agent_config,
        )

        # Execute query
        retrieval_start = time.time()
        response: AgentResponse = await agent.run(
            query=request.query,
            config_id=request.config_id,
            conversation_history=request.conversation_history,
        )
        retrieval_time = int((time.time() - retrieval_start) * 1000)
        total_time = int((time.time() - start_time) * 1000)
        generation_time = total_time - retrieval_time

        # Format sources
        sources = []
        if request.include_sources:
            for chunk in response.sources:
                sources.append(
                    SourceResponse(
                        content=chunk.content,
                        score=chunk.score,
                        metadata=chunk.metadata,
                        source_type=chunk.source_type.value,
                    )
                )

        # Build debug info if requested
        debug = None
        if request.include_debug:
            debug = {
                "steps": [step.to_dict() for step in response.steps],
                "retrieval_time_ms": retrieval_time,
                "generation_time_ms": generation_time,
                "total_time_ms": total_time,
            }

        # Build metadata
        metadata = {
            "agent_type": agent_type,
            "total_duration_ms": response.total_duration_ms,
            "source_count": len(response.sources),
            **response.metadata,
        }

        query_response = QueryResponse(
            answer=response.answer,
            sources=sources,
            debug=debug,
            metadata=metadata,
        )

        # Store in cache if caching is enabled
        if cache_enabled:
            cache_data = {
                "answer": query_response.answer,
                "sources": [s.model_dump() for s in query_response.sources],
                "debug": query_response.debug,
                "metadata": query_response.metadata,
            }
            await query_cache.set(
                request.config_id,
                request.query,
                cache_data,
                ttl_seconds=query_cache_ttl,
            )

        return query_response

    except HTTPException:
        raise
    except LLMContextLengthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM context limit exceeded: {str(e)}",
        )
    except LLMError as e:
        logger.warning("Query execution failed due to LLM provider error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider failure: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )


@router.get("/")
async def query_get(
    http_request: Request,
    query: str = Query(..., description="User query text", max_length=10000),
    config_id: str = Query(..., description="RAG pipeline configuration ID"),
    user_role: Optional[str] = Query(None, description="User role for RBAC"),
):
    """
    Execute a single RAG query via GET request.

    Simpler interface for basic queries without conversation history.
    """
    request = QueryRequest(
        query=query,
        config_id=config_id,
        user_role=user_role,
    )
    return await query(request, http_request)


# Helper function for creating LLM from config
def get_llm_from_config(pipeline_config: Dict[str, Any]):
    """Create LLM instance from pipeline configuration."""
    from app.llm.base import LLMConfig

    llm_config = pipeline_config.get("llm", {})

    provider_str = llm_config.get("provider", "openai")
    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        provider = LLMProvider.OPENAI

    config = LLMConfig(
        model=llm_config.get("model", "gpt-4o-mini"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2048),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url"),
    )

    return get_llm(provider=provider, config=config)


# Helper function for creating agent
def get_agent(
    agent_type: str,
    retriever,
    llm,
    prompt_manager,
    config: Dict[str, Any],
):
    """Create agent instance based on type."""
    from app.agents.naive import NaiveRAGAgent
    from app.agents.react import ReActAgent, ReActConfig
    from app.agents.crag import CRAGAgent, CRAGConfig
    from app.agents.self_rag import SelfRAGAgent, SelfRAGConfig
    from app.agents.multi_query import MultiQueryAgent, MultiQueryConfig
    from app.agents.plan_solve import PlanSolveAgent, PlanSolveConfig
    from app.agents.graph_rag import GraphRAGAgent, GraphRAGConfig
    from app.agents.base import AgentConfig

    agent_type_lower = agent_type.lower()

    if agent_type_lower in ["graph_rag", "graphrag", "graph-rag"]:
        graph_config = GraphRAGConfig.from_dict(config)
        return GraphRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=graph_config,
        )

    elif agent_type_lower in ["naive", "naive_rag", "simple"]:
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

    else:
        # Default to naive
        logger.warning(f"Unknown agent type '{agent_type}', using naive")
        agent_config = AgentConfig.from_dict(config)
        return NaiveRAGAgent(
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=agent_config,
        )
