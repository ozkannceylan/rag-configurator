"""API endpoints for chat with conversation history."""

import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.base import AgentResponse
from app.api.v1.query import get_agent, get_llm_from_config
from app.core.settings import settings
from app.db.mongodb import mongodb
from app.retrieval.factory import get_retriever_from_config
from app.prompts.manager import PromptManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str = Field(..., description="User message")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    user_role: Optional[str] = Field(None, description="User role for RBAC")
    include_sources: bool = Field(True, description="Include source chunks in response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str
    conversation_id: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    conversation_id: str
    messages: List[ChatMessage]
    created_at: str
    updated_at: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Execute a chat message with conversation history.

    This endpoint maintains conversation context across multiple messages,
    allowing for follow-up questions and contextual responses.
    """
    start_time = time.time()

    try:
        # Get database connection
        db = mongodb.get_database()

        # Get or create conversation
        conversation_id = request.conversation_id
        conversation_history = []

        if conversation_id:
            # Load existing conversation
            conv_doc = await db["conversations"].find_one({"_id": conversation_id})
            if conv_doc:
                conversation_history = conv_doc.get("messages", [])
            else:
                # Conversation not found, create new
                conversation_id = None

        if not conversation_id:
            # Create new conversation
            from bson import ObjectId
            conversation_id = str(ObjectId())
            await db["conversations"].insert_one({
                "_id": conversation_id,
                "config_id": request.config_id,
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        # Load configuration
        config_doc = await db["configs"].find_one({"_id": request.config_id})
        if not config_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{request.config_id}' not found",
            )

        pipeline_config = config_doc.get("pipeline_config", {})

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

        # Execute query with conversation history
        response: AgentResponse = await agent.run(
            query=request.message,
            config_id=request.config_id,
            conversation_history=conversation_history,
        )

        # Update conversation in database
        new_messages = [
            {"role": "user", "content": request.message, "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": response.answer, "timestamp": datetime.now(timezone.utc).isoformat()},
        ]

        await db["conversations"].update_one(
            {"_id": conversation_id},
            {
                "$push": {"messages": {"$each": new_messages}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
        )

        # Format sources
        sources = []
        if request.include_sources:
            for chunk in response.sources:
                sources.append({
                    "content": chunk.content,
                    "score": chunk.score,
                    "metadata": chunk.metadata,
                    "source_type": chunk.source_type.value,
                })

        # Build metadata
        metadata = {
            "agent_type": agent_type,
            "total_duration_ms": response.total_duration_ms,
            "source_count": len(response.sources),
            "conversation_turn": len(conversation_history) // 2 + 1,
            **response.metadata,
        }

        return ChatResponse(
            answer=response.answer,
            conversation_id=conversation_id,
            sources=sources,
            metadata=metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat execution failed: {str(e)}",
        )


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str):
    """
    Get conversation history by ID.
    """
    try:
        db = mongodb.get_database()
        conv_doc = await db["conversations"].find_one({"_id": conversation_id})

        if not conv_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found",
            )

        messages = [
            ChatMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp"),
            )
            for msg in conv_doc.get("messages", [])
        ]

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            created_at=conv_doc.get("created_at", ""),
            updated_at=conv_doc.get("updated_at", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get conversation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation history: {str(e)}",
        )


@router.delete("/history/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation by ID.
    """
    try:
        db = mongodb.get_database()
        result = await db["conversations"].delete_one({"_id": conversation_id})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found",
            )

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}",
        )
