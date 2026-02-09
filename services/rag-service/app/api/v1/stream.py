"""API endpoints for streaming responses."""

import logging
import json
from typing import Any, AsyncIterator, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.core.settings import settings
from app.db.mongodb import mongodb
from app.retrieval.factory import get_retriever_from_config
from app.prompts.manager import PromptManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["stream"])


def build_pipeline_config(config_doc: Dict[str, Any]) -> Dict[str, Any]:
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

    return {
        "llm": {
            "provider": llm_data.get("provider", "openai"),
            "model": llm_data.get("model_name") or llm_data.get("model", "gpt-4o-mini"),
            "base_url": llm_data.get("base_url") or getattr(settings, "ollama_base_url", None),
            "api_key": llm_data.get("api_key"),
            "temperature": llm_data.get("temperature", 0.7),
            "max_tokens": llm_data.get("max_tokens", 2048),
        },
        "embedding": {
            "provider": embedding_data.get("provider", "openai"),
            "model": embedding_data.get("model_name") or embedding_data.get("model"),
            "base_url": embedding_data.get("base_url") or getattr(settings, "ollama_base_url", None),
            "api_key": embedding_data.get("api_key"),
            "dimensions": embedding_data.get("dimensions"),
        },
        "retrieval": {
            "method": retrieval_data.get("method", "naive"),
            "top_k": retrieval_data.get("vector", {}).get("top_k", 5),
            "min_score": retrieval_data.get("vector", {}).get("score_threshold", 0.0),
            "embedding_provider": embedding_data.get("provider", "openai"),
            "embedding_model": embedding_data.get("model_name") or embedding_data.get("model"),
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

    query: str = Field(..., description="User query text")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    user_role: Optional[str] = Field(None, description="User role for RBAC")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation messages"
    )


async def stream_response_generator(
    query: str,
    config_id: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Generate streaming response events.

    Yields:
        Events with type: "start", "token", "source", "end"
    """
    try:
        # Get database connection
        db = mongodb.get_database()

        # Load configuration (convert string ID to ObjectId)
        try:
            oid = ObjectId(config_id)
        except Exception:
            oid = config_id
        config_doc = await db["configs"].find_one({"_id": oid})
        if not config_doc:
            yield json.dumps({
                "type": "error",
                "content": f"Configuration '{config_id}' not found",
            })
            return

        pipeline_config = build_pipeline_config(config_doc)

        # Create components
        retriever = get_retriever_from_config(
            db=db,
            pipeline_config=pipeline_config,
        )

        llm = get_llm_from_config(pipeline_config)
        prompt_manager = PromptManager()

        # Get agent
        agent_config = pipeline_config.get("agent", {})
        agent_type = agent_config.get("type", "naive")

        agent = get_agent(
            agent_type=agent_type,
            retriever=retriever,
            llm=llm,
            prompt_manager=prompt_manager,
            config=agent_config,
        )

        # Send start event
        yield json.dumps({
            "type": "start",
            "content": "Starting generation...",
        })

        # Execute agent run first to get sources
        response: AgentResponse = await agent.run(
            query=query,
            config_id=config_id,
            conversation_history=conversation_history,
        )

        # Send source events
        for i, chunk in enumerate(response.sources):
            yield json.dumps({
                "type": "source",
                "content": {
                    "index": i + 1,
                    "content": chunk.content,
                    "score": chunk.score,
                    "metadata": chunk.metadata,
                    "source_type": chunk.source_type.value,
                },
            })

        # Stream the answer word by word
        words = response.answer.split()
        for i, word in enumerate(words):
            # Add space after word except for last word
            text = word + (" " if i < len(words) - 1 else "")
            yield json.dumps({
                "type": "token",
                "content": text,
            })

        # Send end event (mapped to 'done' for frontend compatibility)
        yield json.dumps({
            "type": "done",
            "content": "Generation complete",
            "metadata": {
                "total_duration_ms": response.total_duration_ms,
                "source_count": len(response.sources),
                **response.metadata,
            },
        })

    except Exception as e:
        logger.exception(f"Streaming failed: {e}")
        yield json.dumps({
            "type": "error",
            "content": f"Streaming failed: {str(e)}",
        })


@router.get("/")
async def stream_get(
    query: str = Query(..., description="User query text"),
    config_id: str = Query(..., description="RAG pipeline configuration ID"),
    user_role: Optional[str] = Query(None, description="User role for RBAC"),
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
    async def event_generator():
        async for event in stream_response_generator(
            query=query,
            config_id=config_id,
        ):
            yield event

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.post("/")
async def stream_post(request: StreamRequest):
    """
    Stream a RAG response via Server-Sent Events (POST).

    Same as GET but accepts parameters in request body for larger queries.
    """
    async def event_generator():
        async for event in stream_response_generator(
            query=request.query,
            config_id=request.config_id,
            conversation_history=request.conversation_history,
        ):
            yield event

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
    )
