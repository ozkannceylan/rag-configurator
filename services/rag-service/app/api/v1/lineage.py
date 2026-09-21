"""Data lineage tracking for RAG queries."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.auth import get_authenticated_user_id
from app.db.mongodb import mongodb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lineage", tags=["lineage"])


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------


class SourceFileLineage(BaseModel):
    """Lineage information for a source file."""

    file_name: str | None = None
    file_path: str | None = None
    file_type: str | None = None
    document_id: str = ""


class ChunkLineage(BaseModel):
    """Lineage information for a retrieved chunk."""

    chunk_id: str
    content_preview: str = Field(
        default="", description="First 200 chars of chunk content"
    )
    score: float = 0.0
    source_file: SourceFileLineage | None = None
    chunk_index: int = 0
    used_in_generation: bool = True


class QueryLineage(BaseModel):
    """Full lineage record for a query."""

    query_id: str
    config_id: str
    user_id: str
    query: str
    answer_preview: str = Field(default="", description="First 500 chars of the answer")
    agent_type: str = ""
    query_type: str = ""
    chunks: list[ChunkLineage] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Lineage storage helpers
# ------------------------------------------------------------------


async def store_query_lineage(
    db: Any,
    query_id: str,
    config_id: str,
    user_id: str,
    query: str,
    answer: str,
    sources: list[Any],
    steps: list[Any],
    total_duration_ms: float,
    metadata: dict[str, Any] | None = None,
) -> str:
    """
    Store query lineage in MongoDB.

    Called from agent execution to persist lineage data.

    Args:
        db: MongoDB database instance.
        query_id: Unique query identifier.
        config_id: Pipeline configuration ID.
        user_id: User ID.
        query: Original query text.
        answer: Generated answer text.
        sources: List of RetrievedChunk objects (or dicts).
        steps: List of AgentStep objects (or dicts).
        total_duration_ms: Total execution time.
        metadata: Additional metadata.

    Returns:
        The query_id.
    """
    chunks = []
    for source in sources:
        if hasattr(source, "to_dict"):
            s = source.to_dict()
        elif isinstance(source, dict):
            s = source
        else:
            continue

        chunks.append(
            {
                "chunk_id": s.get("chunk_id", ""),
                "content_preview": s.get("content", "")[:200],
                "score": s.get("score", 0.0),
                "source_file": {
                    "file_name": s.get("file_name"),
                    "file_path": s.get("file_path"),
                    "file_type": s.get("file_type"),
                    "document_id": s.get("document_id", ""),
                },
                "chunk_index": s.get("chunk_index", 0),
                "used_in_generation": True,
            }
        )

    step_dicts = []
    for step in steps:
        if hasattr(step, "to_dict"):
            step_dicts.append(step.to_dict())
        elif isinstance(step, dict):
            step_dicts.append(step)

    doc = {
        "query_id": query_id,
        "config_id": config_id,
        "user_id": user_id,
        "query": query,
        "answer_preview": answer[:500] if answer else "",
        "agent_type": (metadata or {}).get("agent_type", ""),
        "query_type": (metadata or {}).get("query_type", ""),
        "chunks": chunks,
        "steps": step_dicts,
        "total_duration_ms": total_duration_ms,
        "created_at": datetime.now(UTC),
        "metadata": metadata or {},
    }

    collection = db["query_lineage"]
    await collection.insert_one(doc)
    logger.debug("Stored lineage for query %s", query_id)
    return query_id


def generate_query_id() -> str:
    """Generate a unique query ID."""
    return f"q-{uuid.uuid4().hex[:12]}"


# ------------------------------------------------------------------
# API endpoints
# ------------------------------------------------------------------


@router.get("/{query_id}", response_model=QueryLineage)
async def get_lineage(query_id: str, http_request: Request):
    """
    Get full lineage for a query.

    Returns the source files, retrieved chunks with scores, and
    how they were used in generating the answer.
    """
    db = mongodb.get_database()
    user_id = get_authenticated_user_id(http_request)

    collection = db["query_lineage"]
    doc = await collection.find_one({"query_id": query_id})

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lineage for query '{query_id}' not found",
        )

    # Verify ownership
    if doc.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this lineage record",
        )

    return QueryLineage(
        query_id=doc["query_id"],
        config_id=doc.get("config_id", ""),
        user_id=doc.get("user_id", ""),
        query=doc.get("query", ""),
        answer_preview=doc.get("answer_preview", ""),
        agent_type=doc.get("agent_type", ""),
        query_type=doc.get("query_type", ""),
        chunks=[
            ChunkLineage(
                chunk_id=c.get("chunk_id", ""),
                content_preview=c.get("content_preview", ""),
                score=c.get("score", 0.0),
                source_file=(
                    SourceFileLineage(**c["source_file"])
                    if c.get("source_file")
                    else None
                ),
                chunk_index=c.get("chunk_index", 0),
                used_in_generation=c.get("used_in_generation", True),
            )
            for c in doc.get("chunks", [])
        ],
        steps=doc.get("steps", []),
        total_duration_ms=doc.get("total_duration_ms", 0.0),
        created_at=doc.get("created_at"),
        metadata=doc.get("metadata", {}),
    )


@router.get("/config/{config_id}", response_model=list[QueryLineage])
async def list_lineage_by_config(
    config_id: str,
    http_request: Request,
    limit: int = 20,
    offset: int = 0,
):
    """List recent lineage records for a configuration."""
    db = mongodb.get_database()
    user_id = get_authenticated_user_id(http_request)

    collection = db["query_lineage"]
    cursor = (
        collection.find({"config_id": config_id, "user_id": user_id})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )

    results = []
    async for doc in cursor:
        results.append(
            QueryLineage(
                query_id=doc["query_id"],
                config_id=doc.get("config_id", ""),
                user_id=doc.get("user_id", ""),
                query=doc.get("query", ""),
                answer_preview=doc.get("answer_preview", ""),
                agent_type=doc.get("agent_type", ""),
                query_type=doc.get("query_type", ""),
                chunks=[],  # Omit chunks in list view for performance
                steps=[],
                total_duration_ms=doc.get("total_duration_ms", 0.0),
                created_at=doc.get("created_at"),
                metadata=doc.get("metadata", {}),
            )
        )

    return results
