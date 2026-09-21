"""API endpoints for streaming responses."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from sse_starlette.sse import EventSourceResponse

    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    EventSourceResponse = None

from app.agents.base import AgentResponse
from app.api.v1.query import get_agent, get_llm_from_config
from app.core.auth import get_authenticated_user_id, require_config_access
from app.core.settings import settings
from app.db.mongodb import mongodb
from app.llm.base import LLMContextLengthError, LLMError
from app.prompts.manager import PromptManager
from app.retrieval.factory import get_retriever_from_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


def _resolve_base_url(provider: str, config_url: str | None) -> str | None:
    """Resolve base URL, preferring OLLAMA_BASE_URL env var for ollama providers.

    When running in Docker, configs may store localhost URLs that don't work
    inside containers. The OLLAMA_BASE_URL env var (set in docker-compose)
    provides the correct host-reachable URL.
    """
    if provider == "ollama":
        env_url = getattr(settings, "ollama_base_url", None)
        if env_url:
            return env_url
    return config_url


def build_pipeline_config(config_doc: dict[str, Any]) -> dict[str, Any]:
    """
    Build a pipeline_config dict from the actual MongoDB config structure.

    The config in MongoDB stores data under 'models.llm', 'models.embedding',
    'retrieval', 'agent', 'prompts' etc. The RAG pipeline code expects a flat
    'pipeline_config' dict with keys like 'llm', 'embedding', 'retrieval', 'agent'.
    """
    models = config_doc.get("models", {})
    llm_data = models.get("llm", {})
    embedding_data = models.get("embedding", {})
    retrieval_data = config_doc.get("retrieval", {})

    llm_provider = llm_data.get("provider", "openai")
    emb_provider = embedding_data.get("provider", "openai")

    # Local models (Ollama/vLLM) need longer timeouts for model loading + CPU inference
    default_timeout = 300.0 if llm_provider in ("ollama", "vllm") else 60.0

    return {
        "llm": {
            "provider": llm_provider,
            "model": llm_data.get("model_name") or llm_data.get("model", "gpt-4o-mini"),
            "base_url": _resolve_base_url(llm_provider, llm_data.get("base_url")),
            "api_key": llm_data.get("api_key"),
            "temperature": llm_data.get("temperature", 0.7),
            "max_tokens": llm_data.get("max_tokens", 2048),
            "timeout_seconds": llm_data.get("timeout_seconds", default_timeout),
        },
        "embedding": {
            "provider": emb_provider,
            "model": embedding_data.get("model_name") or embedding_data.get("model"),
            "base_url": _resolve_base_url(emb_provider, embedding_data.get("base_url")),
            "api_key": embedding_data.get("api_key"),
            "dimensions": embedding_data.get("dimensions"),
        },
        "retrieval": {
            "method": retrieval_data.get("method", "naive"),
            "top_k": retrieval_data.get("vector", {}).get("top_k", 5),
            "min_score": retrieval_data.get("vector", {}).get("score_threshold", 0.0),
            "embedding_provider": embedding_data.get("provider", "openai"),
            "embedding_model": embedding_data.get("model_name")
            or embedding_data.get("model"),
            "keyword": retrieval_data.get("keyword", {}),
            "graph": retrieval_data.get("graph", {}),
        },
        "agent": {
            "type": config_doc.get("agent", {}).get("template", "naive"),
            **{k: v for k, v in config_doc.get("agent", {}).items() if k != "template"},
        },
        "prompts": config_doc.get("prompts", {}),
    }


class StreamRequest(BaseModel):
    """Request model for streaming endpoint."""

    query: str = Field(..., description="User query text", max_length=10000)
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    user_role: str | None = Field(None, description="User role for RBAC")
    conversation_history: list[dict[str, str]] | None = Field(
        None, description="Previous conversation messages"
    )


async def build_stream_events(
    query: str,
    config_id: str,
    user_id: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> list[str]:
    """
    Build SSE payloads for a streaming response.
    """
    db = mongodb.get_database()
    config_doc = await require_config_access(db, config_id, user_id)
    pipeline_config = build_pipeline_config(config_doc)

    retriever = get_retriever_from_config(
        db=db,
        pipeline_config=pipeline_config,
    )
    llm = get_llm_from_config(pipeline_config)
    prompt_manager = PromptManager()

    agent_config = pipeline_config.get("agent", {})
    agent_type = agent_config.get("type", "naive")

    agent = get_agent(
        agent_type=agent_type,
        retriever=retriever,
        llm=llm,
        prompt_manager=prompt_manager,
        config=agent_config,
    )

    response: AgentResponse = await agent.run(
        query=query,
        config_id=config_id,
        conversation_history=conversation_history,
    )

    events = [
        json.dumps(
            {
                "type": "start",
                "content": "Starting generation...",
            }
        )
    ]

    for i, chunk in enumerate(response.sources):
        events.append(
            json.dumps(
                {
                    "type": "source",
                    "content": {
                        "index": i + 1,
                        "content": chunk.content,
                        "score": chunk.score,
                        "metadata": chunk.metadata,
                        "source_type": chunk.source_type.value,
                    },
                }
            )
        )

    words = response.answer.split()
    for i, word in enumerate(words):
        text = word + (" " if i < len(words) - 1 else "")
        events.append(
            json.dumps(
                {
                    "type": "token",
                    "content": text,
                }
            )
        )

    events.append(
        json.dumps(
            {
                "type": "done",
                "content": "Generation complete",
                "metadata": {
                    "total_duration_ms": response.total_duration_ms,
                    "source_count": len(response.sources),
                    **response.metadata,
                },
            }
        )
    )

    return events


async def stream_response_generator(events: list[str]) -> AsyncIterator[str]:
    """Yield prebuilt SSE events."""
    for event in events:
        yield event


@router.get("/")
async def stream_get(
    http_request: Request,
    query: str = Query(..., description="User query text", max_length=10000),
    config_id: str = Query(..., description="RAG pipeline configuration ID"),
    user_role: str | None = Query(None, description="User role for RBAC"),
):
    """
    Stream a RAG response via Server-Sent Events.

    This endpoint provides real-time streaming of the generated response
    along with source information.

    Event types:
    - `start`: Generation started
    - `source`: Retrieved source chunk
    - `token`: Next token/word of the answer
    - `end`: Generation complete
    - `error`: Error occurred
    """
    user_id = get_authenticated_user_id(http_request)

    try:
        events = await asyncio.wait_for(
            build_stream_events(
                query=query,
                config_id=config_id,
                user_id=user_id,
            ),
            timeout=120,
        )
    except LLMContextLengthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM context limit exceeded: {str(e)}",
        )
    except LLMError as e:
        logger.warning("Streaming failed due to LLM provider error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider failure: {str(e)}",
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Streaming request timed out after 120 seconds",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Streaming failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming failed: {str(e)}",
        )

    generator = stream_response_generator(events)
    if SSE_AVAILABLE:
        return EventSourceResponse(generator, media_type="text/event-stream")
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/")
async def stream_post(request: StreamRequest, http_request: Request):
    """
    Stream a RAG response via Server-Sent Events (POST).

    Same as GET but accepts parameters in request body for larger queries.
    """
    user_id = get_authenticated_user_id(http_request)

    try:
        events = await asyncio.wait_for(
            build_stream_events(
                query=request.query,
                config_id=request.config_id,
                user_id=user_id,
                conversation_history=request.conversation_history,
            ),
            timeout=120,
        )
    except LLMContextLengthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM context limit exceeded: {str(e)}",
        )
    except LLMError as e:
        logger.warning("Streaming failed due to LLM provider error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider failure: {str(e)}",
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Streaming request timed out after 120 seconds",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Streaming failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming failed: {str(e)}",
        )

    generator = stream_response_generator(events)
    if SSE_AVAILABLE:
        return EventSourceResponse(generator, media_type="text/event-stream")
    return StreamingResponse(generator, media_type="text/event-stream")
