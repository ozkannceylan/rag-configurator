"""Ingestion API endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.db.mongodb import get_database
from app.storage.models import IngestionRecord, IngestionStatus
from app.storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================


class StartIngestionResponse(BaseModel):
    """Response for starting ingestion."""

    task_id: str
    ingestion_id: str
    config_id: str
    status: str = "pending"
    message: str = "Ingestion started"


class IngestionStatusResponse(BaseModel):
    """Response for ingestion status."""

    config_id: str
    ingestion_id: Optional[str] = None
    task_id: Optional[str] = None
    status: str
    progress: float = 0.0
    current_step: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class CancelIngestionResponse(BaseModel):
    """Response for cancelling ingestion."""

    config_id: str
    ingestion_id: str
    message: str = "Ingestion cancelled"
    success: bool = True


class RetryIngestionResponse(BaseModel):
    """Response for retrying ingestion."""

    task_id: str
    ingestion_id: str
    config_id: str
    message: str = "Ingestion restarted"


class IngestionLogEntry(BaseModel):
    """Log entry for ingestion."""

    timestamp: str
    level: str
    message: str
    file_path: Optional[str] = None


class IngestionLogsResponse(BaseModel):
    """Response for ingestion logs."""

    config_id: str
    ingestion_id: Optional[str] = None
    logs: List[IngestionLogEntry] = []
    total_count: int = 0


class IngestionStatsResponse(BaseModel):
    """Response for ingestion statistics."""

    config_id: str
    ingestion_id: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    processing_time_seconds: Optional[float] = None
    files_by_type: Dict[str, int] = Field(default_factory=dict)
    avg_chunks_per_file: float = 0.0


class IngestionHistoryEntry(BaseModel):
    """Entry in ingestion history."""

    ingestion_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0


class IngestionHistoryResponse(BaseModel):
    """Response for ingestion history."""

    config_id: str
    history: List[IngestionHistoryEntry] = []
    total_count: int = 0


# ==================== Helper Functions ====================


async def get_config(db: AsyncIOMotorDatabase, config_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration by ID."""
    configs = db["configs"]

    # Try ObjectId first
    try:
        config = await configs.find_one({"_id": ObjectId(config_id)})
        if config:
            config["_id"] = str(config["_id"])
            return config
    except Exception:
        pass

    # Try string ID
    config = await configs.find_one({"_id": config_id})
    if config:
        config["_id"] = str(config["_id"])
        return config

    # Try id field
    config = await configs.find_one({"id": config_id})
    if config:
        config["_id"] = str(config["_id"])
        return config

    return None


async def get_latest_ingestion(
    db: AsyncIOMotorDatabase, config_id: str
) -> Optional[Dict[str, Any]]:
    """Get the latest ingestion for a config."""
    ingestions = db["ingestions"]
    ingestion = await ingestions.find_one(
        {"config_id": config_id},
        sort=[("created_at", -1)],
    )
    if ingestion:
        ingestion["_id"] = str(ingestion["_id"])
    return ingestion


async def get_running_ingestion(
    db: AsyncIOMotorDatabase, config_id: str
) -> Optional[Dict[str, Any]]:
    """Get a running ingestion for a config."""
    ingestions = db["ingestions"]
    ingestion = await ingestions.find_one(
        {
            "config_id": config_id,
            "status": {"$in": ["pending", "running"]},
        }
    )
    if ingestion:
        ingestion["_id"] = str(ingestion["_id"])
    return ingestion


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string."""
    if dt:
        return dt.isoformat()
    return None


# ==================== Endpoints ====================


@router.post(
    "/{config_id}/start",
    response_model=StartIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_ingestion(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> StartIngestionResponse:
    """
    Start ingestion for a configuration.

    Triggers a Celery task to process all documents in the data source.
    """
    # Validate config exists
    config = await get_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found: {config_id}",
        )

    # Check if ingestion already running
    running = await get_running_ingestion(db, config_id)
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ingestion already in progress: {running['_id']}",
        )

    # Get user_id from config or use default
    user_id = config.get("user_id", "system")

    # Create ingestion record
    vector_store = VectorStore(db)
    ingestion = IngestionRecord(
        config_id=config_id,
        user_id=user_id,
        status=IngestionStatus.PENDING,
        config_snapshot=config,
    )
    ingestion_id = await vector_store.create_ingestion(ingestion)

    # Start Celery task
    try:
        from app.tasks.ingestion_task import run_ingestion

        task = run_ingestion.delay(config_id, user_id, ingestion_id)
        task_id = task.id

        # Update ingestion with task ID
        await db["ingestions"].update_one(
            {"_id": ingestion_id},
            {"$set": {"celery_task_id": task_id}},
        )
    except ImportError:
        # Celery not available - for testing without Celery
        logger.warning("Celery not available, ingestion will not run")
        task_id = f"mock-task-{ingestion_id}"

        await db["ingestions"].update_one(
            {"_id": ingestion_id},
            {"$set": {"celery_task_id": task_id}},
        )

    logger.info(f"Started ingestion {ingestion_id} for config {config_id}")

    return StartIngestionResponse(
        task_id=task_id,
        ingestion_id=ingestion_id,
        config_id=config_id,
        status="pending",
        message="Ingestion started",
    )


@router.get(
    "/{config_id}/status",
    response_model=IngestionStatusResponse,
)
async def get_ingestion_status(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> IngestionStatusResponse:
    """
    Get current ingestion status for a configuration.

    Returns the latest ingestion job status and progress.
    """
    # Get latest ingestion
    ingestion = await get_latest_ingestion(db, config_id)

    if not ingestion:
        return IngestionStatusResponse(
            config_id=config_id,
            status="none",
            progress=0.0,
        )

    # Calculate progress
    total_files = ingestion.get("total_files", 0)
    processed_files = ingestion.get("processed_files", 0)
    progress = (processed_files / total_files * 100) if total_files > 0 else 0.0

    return IngestionStatusResponse(
        config_id=config_id,
        ingestion_id=ingestion["_id"],
        task_id=ingestion.get("celery_task_id"),
        status=ingestion.get("status", "unknown"),
        progress=progress,
        current_step=ingestion.get("current_step"),
        total_files=total_files,
        processed_files=processed_files,
        failed_files=ingestion.get("failed_files", 0),
        total_chunks=ingestion.get("total_chunks", 0),
        started_at=format_datetime(ingestion.get("started_at")),
        completed_at=format_datetime(ingestion.get("completed_at")),
        error=ingestion.get("error_message"),
    )


@router.post(
    "/{config_id}/cancel",
    response_model=CancelIngestionResponse,
)
async def cancel_ingestion(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> CancelIngestionResponse:
    """
    Cancel a running ingestion.

    Revokes the Celery task and updates status to cancelled.
    """
    # Get running ingestion
    ingestion = await get_running_ingestion(db, config_id)

    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No running ingestion found for this configuration",
        )

    ingestion_id = ingestion["_id"]
    task_id = ingestion.get("celery_task_id")

    # Revoke Celery task if available
    if task_id:
        try:
            from app.core.celery_app import celery_app

            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Revoked Celery task {task_id}")
        except ImportError:
            logger.warning("Celery not available for task revocation")
        except Exception as e:
            logger.error(f"Failed to revoke task: {e}")

    # Update status to cancelled
    await db["ingestions"].update_one(
        {"_id": ingestion_id},
        {
            "$set": {
                "status": IngestionStatus.CANCELLED.value,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    logger.info(f"Cancelled ingestion {ingestion_id}")

    return CancelIngestionResponse(
        config_id=config_id,
        ingestion_id=ingestion_id,
        message="Ingestion cancelled",
        success=True,
    )


@router.post(
    "/{config_id}/retry",
    response_model=RetryIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_ingestion(
    config_id: str,
    clear_data: bool = Query(
        default=False,
        description="Clear previous ingestion data before retrying",
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> RetryIngestionResponse:
    """
    Retry a failed ingestion.

    Only allowed if the last ingestion status is 'failed'.
    Optionally clears previous data before retrying.
    """
    # Get latest ingestion
    ingestion = await get_latest_ingestion(db, config_id)

    if not ingestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ingestion found for this configuration",
        )

    if ingestion.get("status") not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry ingestion with status: {ingestion.get('status')}",
        )

    # Optionally clear previous data
    if clear_data:
        vector_store = VectorStore(db)
        await vector_store.delete_documents_by_config(config_id)
        logger.info(f"Cleared previous data for config {config_id}")

    # Get config
    config = await get_config(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found: {config_id}",
        )

    user_id = config.get("user_id", "system")

    # Create new ingestion record
    vector_store = VectorStore(db)
    new_ingestion = IngestionRecord(
        config_id=config_id,
        user_id=user_id,
        status=IngestionStatus.PENDING,
        config_snapshot=config,
    )
    ingestion_id = await vector_store.create_ingestion(new_ingestion)

    # Start Celery task
    try:
        from app.tasks.ingestion_task import run_ingestion

        task = run_ingestion.delay(config_id, user_id, ingestion_id)
        task_id = task.id

        await db["ingestions"].update_one(
            {"_id": ingestion_id},
            {"$set": {"celery_task_id": task_id}},
        )
    except ImportError:
        task_id = f"mock-task-{ingestion_id}"
        await db["ingestions"].update_one(
            {"_id": ingestion_id},
            {"$set": {"celery_task_id": task_id}},
        )

    logger.info(f"Retried ingestion {ingestion_id} for config {config_id}")

    return RetryIngestionResponse(
        task_id=task_id,
        ingestion_id=ingestion_id,
        config_id=config_id,
        message="Ingestion restarted",
    )


@router.get(
    "/{config_id}/logs",
    response_model=IngestionLogsResponse,
)
async def get_ingestion_logs(
    config_id: str,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    level: Optional[str] = Query(default=None, description="Filter by log level"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> IngestionLogsResponse:
    """
    Get ingestion logs/events.

    Returns logs from the latest ingestion job.
    """
    # Get latest ingestion
    ingestion = await get_latest_ingestion(db, config_id)

    if not ingestion:
        return IngestionLogsResponse(
            config_id=config_id,
            logs=[],
            total_count=0,
        )

    # Get errors as logs
    logs: List[IngestionLogEntry] = []
    errors = ingestion.get("errors", [])
    warnings = ingestion.get("warnings", [])

    for error in errors:
        logs.append(
            IngestionLogEntry(
                timestamp=error.get("timestamp", ""),
                level="ERROR",
                message=error.get("error", "Unknown error"),
                file_path=error.get("file_path"),
            )
        )

    for warning in warnings:
        if isinstance(warning, str):
            logs.append(
                IngestionLogEntry(
                    timestamp="",
                    level="WARNING",
                    message=warning,
                )
            )
        elif isinstance(warning, dict):
            logs.append(
                IngestionLogEntry(
                    timestamp=warning.get("timestamp", ""),
                    level="WARNING",
                    message=warning.get("message", ""),
                    file_path=warning.get("file_path"),
                )
            )

    # Add status change logs
    if ingestion.get("started_at"):
        logs.append(
            IngestionLogEntry(
                timestamp=format_datetime(ingestion.get("started_at")) or "",
                level="INFO",
                message="Ingestion started",
            )
        )

    if ingestion.get("completed_at"):
        status_msg = f"Ingestion {ingestion.get('status', 'completed')}"
        logs.append(
            IngestionLogEntry(
                timestamp=format_datetime(ingestion.get("completed_at")) or "",
                level="INFO" if ingestion.get("status") == "completed" else "ERROR",
                message=status_msg,
            )
        )

    # Filter by level if specified
    if level:
        logs = [log for log in logs if log.level.upper() == level.upper()]

    # Sort by timestamp descending
    logs.sort(key=lambda x: x.timestamp, reverse=True)

    total_count = len(logs)

    # Apply pagination
    logs = logs[offset : offset + limit]

    return IngestionLogsResponse(
        config_id=config_id,
        ingestion_id=ingestion["_id"],
        logs=logs,
        total_count=total_count,
    )


@router.get(
    "/{config_id}/stats",
    response_model=IngestionStatsResponse,
)
async def get_ingestion_stats(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> IngestionStatsResponse:
    """
    Get detailed ingestion statistics.

    Returns comprehensive stats from the latest ingestion job.
    """
    # Get latest ingestion
    ingestion = await get_latest_ingestion(db, config_id)

    if not ingestion:
        return IngestionStatsResponse(config_id=config_id)

    # Get document statistics
    documents = db["documents"]
    doc_pipeline = [
        {"$match": {"config_id": config_id}},
        {
            "$group": {
                "_id": "$file_type",
                "count": {"$sum": 1},
            }
        },
    ]
    files_by_type: Dict[str, int] = {}
    async for doc in documents.aggregate(doc_pipeline):
        file_type = doc["_id"] or "unknown"
        files_by_type[file_type] = doc["count"]

    # Calculate stats
    total_files = ingestion.get("total_files", 0)
    processed_files = ingestion.get("processed_files", 0)
    failed_files = ingestion.get("failed_files", 0)
    total_chunks = ingestion.get("total_chunks", 0)

    # Calculate processing time
    processing_time = None
    if ingestion.get("started_at") and ingestion.get("completed_at"):
        start = ingestion["started_at"]
        end = ingestion["completed_at"]
        if isinstance(start, datetime) and isinstance(end, datetime):
            processing_time = (end - start).total_seconds()

    # Calculate averages
    avg_chunks = total_chunks / processed_files if processed_files > 0 else 0.0

    # Get graph stats
    graph_nodes = 0
    graph_edges = 0
    try:
        graph_nodes = await db["graph_nodes"].count_documents({"config_id": config_id})
        graph_edges = await db["graph_edges"].count_documents({"config_id": config_id})
    except Exception:
        pass

    return IngestionStatsResponse(
        config_id=config_id,
        ingestion_id=ingestion["_id"],
        total_files=total_files,
        processed_files=processed_files,
        failed_files=failed_files,
        skipped_files=total_files - processed_files - failed_files,
        total_chunks=total_chunks,
        total_embeddings=total_chunks,  # 1:1 with chunks
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        processing_time_seconds=processing_time,
        files_by_type=files_by_type,
        avg_chunks_per_file=avg_chunks,
    )


@router.get(
    "/{config_id}/history",
    response_model=IngestionHistoryResponse,
)
async def get_ingestion_history(
    config_id: str,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> IngestionHistoryResponse:
    """
    Get ingestion history for a configuration.

    Returns a list of past ingestion jobs.
    """
    ingestions = db["ingestions"]

    # Get total count
    total_count = await ingestions.count_documents({"config_id": config_id})

    # Get history
    cursor = (
        ingestions.find({"config_id": config_id})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )

    history: List[IngestionHistoryEntry] = []
    async for doc in cursor:
        history.append(
            IngestionHistoryEntry(
                ingestion_id=str(doc["_id"]),
                status=doc.get("status", "unknown"),
                started_at=format_datetime(doc.get("started_at")),
                completed_at=format_datetime(doc.get("completed_at")),
                total_files=doc.get("total_files", 0),
                processed_files=doc.get("processed_files", 0),
                failed_files=doc.get("failed_files", 0),
            )
        )

    return IngestionHistoryResponse(
        config_id=config_id,
        history=history,
        total_count=total_count,
    )


@router.delete(
    "/{config_id}/data",
    status_code=status.HTTP_200_OK,
)
async def delete_ingestion_data(
    config_id: str,
    include_history: bool = Query(
        default=False,
        description="Also delete ingestion history records",
    ),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Dict[str, Any]:
    """
    Delete all ingested data for a configuration.

    Removes documents, chunks, and optionally ingestion history.
    """
    # Check if ingestion is running
    running = await get_running_ingestion(db, config_id)
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete data while ingestion is running",
        )

    vector_store = VectorStore(db)
    deleted_docs = await vector_store.delete_documents_by_config(config_id)

    # Delete graph data
    deleted_nodes = 0
    deleted_edges = 0
    try:
        from app.storage.graph_store import GraphStore

        graph_store = GraphStore(db)
        deleted_nodes = await graph_store.delete_nodes_by_config(config_id)
    except Exception as e:
        logger.error(f"Error deleting graph data: {e}")

    # Delete history if requested
    deleted_ingestions = 0
    if include_history:
        result = await db["ingestions"].delete_many({"config_id": config_id})
        deleted_ingestions = result.deleted_count

    logger.info(
        f"Deleted data for config {config_id}: "
        f"{deleted_docs} docs, {deleted_nodes} nodes, {deleted_ingestions} ingestions"
    )

    return {
        "config_id": config_id,
        "deleted_documents": deleted_docs,
        "deleted_graph_nodes": deleted_nodes,
        "deleted_ingestions": deleted_ingestions,
        "message": "Data deleted successfully",
    }
