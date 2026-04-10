"""Vector store for chunks and embeddings in MongoDB."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.storage.models import (
    ChunkRecord,
    DocumentRecord,
    IngestionRecord,
    IngestionStatus,
    SearchResult,
)

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Storage layer for documents, chunks, and embeddings.

    Uses MongoDB collections:
    - documents: Processed file records
    - chunks: Text chunks with embeddings
    - ingestion_jobs: Ingestion job tracking
    """

    DOCUMENTS_COLLECTION = "documents"
    CHUNKS_COLLECTION = "chunks"
    INGESTIONS_COLLECTION = "ingestion_jobs"

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize vector store with database connection.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.documents = db[self.DOCUMENTS_COLLECTION]
        self.chunks = db[self.CHUNKS_COLLECTION]
        self.ingestions = db[self.INGESTIONS_COLLECTION]

    async def initialize_indexes(self) -> None:
        """Create necessary indexes for efficient queries."""
        logger.info("Creating vector store indexes...")

        # Documents indexes
        await self.documents.create_index("config_id")
        await self.documents.create_index("user_id")
        await self.documents.create_index("content_hash")
        await self.documents.create_index("ingestion_id")
        await self.documents.create_index(
            [("config_id", 1), ("file_path", 1)],
            unique=True,
        )

        # Chunks indexes
        await self.chunks.create_index("config_id")
        await self.chunks.create_index("document_id")
        await self.chunks.create_index("user_id")
        await self.chunks.create_index("ingestion_id")
        await self.chunks.create_index("folder_path")
        await self.chunks.create_index([("config_id", 1), ("document_id", 1)])
        await self.chunks.create_index(
            [("config_id", 1), ("document_id", 1), ("chunk_index", 1)],
            unique=True,
        )

        # Ingestions indexes
        await self.ingestions.create_index("config_id")
        await self.ingestions.create_index("user_id")
        await self.ingestions.create_index("status")
        await self.ingestions.create_index("celery_task_id")
        await self.ingestions.create_index("idempotency_key", unique=True, sparse=True)

        logger.info("Vector store indexes created")

    # ==================== Document Operations ====================

    async def store_document(self, doc: DocumentRecord) -> str:
        """
        Store a document record.

        Args:
            doc: Document record to store

        Returns:
            Inserted document ID
        """
        data = doc.to_mongo()
        if "_id" not in data or not data["_id"]:
            data["_id"] = str(ObjectId())

        result = await self.documents.insert_one(data)
        doc_id = str(result.inserted_id)

        logger.debug(f"Stored document: {doc_id} ({doc.file_name})")
        return doc_id

    async def get_document(self, document_id: str) -> Optional[DocumentRecord]:
        """Get a document by ID."""
        doc = await self.documents.find_one({"_id": document_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return DocumentRecord(**doc)
        return None

    async def get_documents_by_config(
        self, config_id: str, skip: int = 0, limit: int = 100
    ) -> List[DocumentRecord]:
        """Get all documents for a config."""
        cursor = self.documents.find({"config_id": config_id}).skip(skip).limit(limit)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(DocumentRecord(**doc))
        return documents

    async def document_exists(self, config_id: str, content_hash: str) -> bool:
        """Check if a document with the same content already exists."""
        count = await self.documents.count_documents(
            {"config_id": config_id, "content_hash": content_hash}
        )
        return count > 0

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks."""
        # Delete chunks first
        await self.chunks.delete_many({"document_id": document_id})

        # Delete document
        result = await self.documents.delete_one({"_id": document_id})
        return result.deleted_count > 0

    async def delete_documents_by_config(self, config_id: str) -> int:
        """Delete all documents and chunks for a config."""
        # Delete chunks
        await self.chunks.delete_many({"config_id": config_id})

        # Delete documents
        result = await self.documents.delete_many({"config_id": config_id})
        return result.deleted_count

    # ==================== Chunk Operations ====================

    async def store_chunks(self, chunks: List[ChunkRecord]) -> List[str]:
        """
        Store multiple chunk records.

        Args:
            chunks: List of chunk records to store

        Returns:
            List of inserted chunk IDs
        """
        if not chunks:
            return []

        documents = []
        for chunk in chunks:
            data = chunk.to_mongo()
            if "_id" not in data or not data["_id"]:
                data["_id"] = str(ObjectId())
            documents.append(data)

        result = await self.chunks.insert_many(documents)
        chunk_ids = [str(id) for id in result.inserted_ids]

        logger.debug(f"Stored {len(chunk_ids)} chunks")
        return chunk_ids

    async def store_chunk(self, chunk: ChunkRecord) -> str:
        """Store a single chunk record."""
        ids = await self.store_chunks([chunk])
        return ids[0] if ids else ""

    async def get_chunk(self, chunk_id: str) -> Optional[ChunkRecord]:
        """Get a chunk by ID."""
        doc = await self.chunks.find_one({"_id": chunk_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return ChunkRecord(**doc)
        return None

    async def get_chunks_by_document(
        self, document_id: str, include_embeddings: bool = False
    ) -> List[ChunkRecord]:
        """Get all chunks for a document."""
        projection = None if include_embeddings else {"embedding": 0}

        cursor = self.chunks.find(
            {"document_id": document_id}, projection
        ).sort("chunk_index", 1)

        chunks = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if not include_embeddings:
                doc["embedding"] = []
            chunks.append(ChunkRecord(**doc))
        return chunks

    async def get_chunks_by_config(
        self,
        config_id: str,
        skip: int = 0,
        limit: int = 100,
        include_embeddings: bool = False,
    ) -> List[ChunkRecord]:
        """Get chunks for a config."""
        projection = None if include_embeddings else {"embedding": 0}

        cursor = (
            self.chunks.find({"config_id": config_id}, projection)
            .skip(skip)
            .limit(limit)
        )

        chunks = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if not include_embeddings:
                doc["embedding"] = []
            chunks.append(ChunkRecord(**doc))
        return chunks

    async def count_chunks_by_config(self, config_id: str) -> int:
        """Count total chunks for a config."""
        return await self.chunks.count_documents({"config_id": config_id})

    async def update_chunk_embedding(
        self, chunk_id: str, embedding: List[float], model: str, dimensions: int
    ) -> bool:
        """Update a chunk's embedding."""
        result = await self.chunks.update_one(
            {"_id": chunk_id},
            {
                "$set": {
                    "embedding": embedding,
                    "embedding_model": model,
                    "embedding_dimensions": dimensions,
                }
            },
        )
        return result.modified_count > 0

    # ==================== Ingestion Operations ====================

    async def create_ingestion(self, ingestion: IngestionRecord) -> str:
        """Create a new ingestion record.

        Handles concurrent duplicate inserts gracefully by returning
        the existing record when a unique-index collision occurs on
        ``idempotency_key``.
        """
        data = ingestion.to_mongo()
        if "_id" not in data or not data["_id"]:
            data["_id"] = str(ObjectId())

        # Remove null idempotency_key so the sparse unique index skips it
        if data.get("idempotency_key") is None:
            data.pop("idempotency_key", None)

        try:
            result = await self.ingestions.insert_one(data)
            return str(result.inserted_id)
        except DuplicateKeyError:
            # Another request won the race — return the existing record.
            idem_key = data.get("idempotency_key")
            if idem_key is not None:
                existing = await self.ingestions.find_one(
                    {"idempotency_key": idem_key}
                )
                if existing:
                    return str(existing["_id"])
            # Fallback: re-raise if we somehow can't find the duplicate.
            raise

    async def get_ingestion(self, ingestion_id: str) -> Optional[IngestionRecord]:
        """Get an ingestion by ID."""
        doc = await self.ingestions.find_one({"_id": ingestion_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return IngestionRecord(**doc)
        return None

    async def get_ingestion_by_task(
        self, task_id: str
    ) -> Optional[IngestionRecord]:
        """Get ingestion by Celery task ID."""
        doc = await self.ingestions.find_one({"celery_task_id": task_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return IngestionRecord(**doc)
        return None

    async def get_ingestions_by_config(
        self, config_id: str, skip: int = 0, limit: int = 20
    ) -> List[IngestionRecord]:
        """Get ingestions for a config."""
        cursor = (
            self.ingestions.find({"config_id": config_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

        ingestions = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            ingestions.append(IngestionRecord(**doc))
        return ingestions

    async def update_ingestion_status(
        self,
        ingestion_id: str,
        status: IngestionStatus,
        **kwargs: Any,
    ) -> bool:
        """Update ingestion status and optional fields."""
        update_data = {
            "status": status.value if isinstance(status, IngestionStatus) else status,
            "updated_at": datetime.utcnow(),
        }

        # Handle specific status transitions
        if status == IngestionStatus.RUNNING and "started_at" not in kwargs:
            update_data["started_at"] = datetime.utcnow()
        elif status in (
            IngestionStatus.COMPLETED,
            IngestionStatus.FAILED,
            IngestionStatus.CANCELLED,
        ):
            if "completed_at" not in kwargs:
                update_data["completed_at"] = datetime.utcnow()

        # Add any additional fields
        update_data.update(kwargs)

        result = await self.ingestions.update_one(
            {"_id": ingestion_id}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def update_ingestion_progress(
        self,
        ingestion_id: str,
        processed_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> bool:
        """Update ingestion progress counters."""
        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow()}

        if processed_files is not None:
            update_data["processed_files"] = processed_files
        if failed_files is not None:
            update_data["failed_files"] = failed_files
        if total_chunks is not None:
            update_data["total_chunks"] = total_chunks

        result = await self.ingestions.update_one(
            {"_id": ingestion_id}, {"$set": update_data}
        )
        return result.modified_count > 0

    async def increment_ingestion_progress(
        self,
        ingestion_id: str,
        processed_files: int = 0,
        failed_files: int = 0,
        total_chunks: int = 0,
    ) -> bool:
        """Increment ingestion progress counters atomically."""
        inc_data = {}
        if processed_files:
            inc_data["processed_files"] = processed_files
        if failed_files:
            inc_data["failed_files"] = failed_files
        if total_chunks:
            inc_data["total_chunks"] = total_chunks

        if not inc_data:
            return False

        result = await self.ingestions.update_one(
            {"_id": ingestion_id},
            {
                "$inc": inc_data,
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    async def add_ingestion_error(
        self, ingestion_id: str, file_path: str, error: str
    ) -> bool:
        """Add an error to ingestion record."""
        error_entry = {
            "file_path": file_path,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }

        result = await self.ingestions.update_one(
            {"_id": ingestion_id},
            {
                "$push": {"errors": error_entry},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
        return result.modified_count > 0

    # ==================== Search Operations ====================

    async def search_by_embedding(
        self,
        config_id: str,
        embedding: List[float],
        limit: int = 10,
        min_score: float = 0.0,
        folder_paths: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Search for similar chunks using vector similarity.

        Note: This is a basic implementation using MongoDB.
        For production, consider using a dedicated vector database
        like Pinecone, Weaviate, or MongoDB Atlas Vector Search.

        Args:
            config_id: Config to search within
            embedding: Query embedding vector
            limit: Maximum results to return
            min_score: Minimum similarity score
            folder_paths: Optional folder paths for RBAC filtering

        Returns:
            List of search results sorted by similarity
        """
        # Build query filter
        query: Dict[str, Any] = {
            "config_id": config_id,
            "embedding": {"$exists": True, "$ne": []},
        }

        # Add folder path filter for RBAC
        if folder_paths:
            query["folder_path"] = {"$in": folder_paths}

        # Get chunks with embeddings
        cursor = self.chunks.find(query)
        chunks = []
        async for doc in cursor:
            chunks.append(doc)

        # Calculate cosine similarity
        results = []
        for chunk in chunks:
            chunk_embedding = chunk.get("embedding", [])
            if not chunk_embedding:
                continue

            score = self._cosine_similarity(embedding, chunk_embedding)
            if score >= min_score:
                results.append(
                    SearchResult(
                        chunk_id=str(chunk["_id"]),
                        document_id=chunk.get("document_id", ""),
                        config_id=chunk.get("config_id", ""),
                        content=chunk.get("content", ""),
                        score=score,
                        metadata=chunk.get("metadata", {}),
                        chunk_index=chunk.get("chunk_index", 0),
                    )
                )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    # ==================== Stats Operations ====================

    async def get_config_stats(self, config_id: str) -> Dict[str, Any]:
        """Get statistics for a config."""
        doc_count = await self.documents.count_documents({"config_id": config_id})
        chunk_count = await self.chunks.count_documents({"config_id": config_id})

        # Get latest ingestion
        latest_ingestion = await self.ingestions.find_one(
            {"config_id": config_id}, sort=[("created_at", -1)]
        )

        return {
            "config_id": config_id,
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "latest_ingestion": (
                {
                    "id": str(latest_ingestion["_id"]),
                    "status": latest_ingestion.get("status"),
                    "created_at": latest_ingestion.get("created_at"),
                }
                if latest_ingestion
                else None
            ),
        }
