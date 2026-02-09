"""Vector retriever using MongoDB Atlas Vector Search or cosine similarity."""

import logging
import math
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievedChunk,
    SourceType,
)

logger = logging.getLogger(__name__)


class VectorRetriever(BaseRetriever):
    """
    Vector similarity retriever for MongoDB.

    Supports two modes:
    1. MongoDB Atlas Vector Search ($vectorSearch) - for production
    2. In-memory cosine similarity - for development without Atlas

    The retriever automatically falls back to cosine similarity if
    vector search index is not available.
    """

    CHUNKS_COLLECTION = "chunks"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: Optional[RetrievalConfig] = None,
        embedder: Optional[Any] = None,
    ):
        """
        Initialize vector retriever.

        Args:
            db: MongoDB database instance
            config: Retrieval configuration
            embedder: Embedding provider instance
        """
        super().__init__(config)
        self.db = db
        self.chunks = db[self.CHUNKS_COLLECTION]
        self._embedder = embedder
        self._use_atlas_search: Optional[bool] = None

    async def _get_embedder(self):
        """Get or create embedder instance."""
        if self._embedder is None:
            # Lazy import to avoid circular dependencies
            from app.retrieval.embedder import get_embedder

            self._embedder = await get_embedder(
                provider=self.config.embedding_provider,
                model=self.config.embedding_model,
            )
        return self._embedder

    async def close(self) -> None:
        """Clean up resources."""
        if self._embedder and hasattr(self._embedder, "close"):
            await self._embedder.close()

    async def _check_atlas_search(self) -> bool:
        """Check if MongoDB Atlas Vector Search is available."""
        if self._use_atlas_search is not None:
            return self._use_atlas_search

        try:
            # Try a simple vector search to check if index exists
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.config.vector_index_name,
                        "path": "embedding",
                        "queryVector": [0.0] * 1536,  # Dummy vector
                        "numCandidates": 1,
                        "limit": 1,
                    }
                },
                {"$limit": 1},
            ]
            await self.chunks.aggregate(pipeline).to_list(length=1)
            self._use_atlas_search = True
            logger.info("MongoDB Atlas Vector Search is available")
        except Exception as e:
            logger.info(f"MongoDB Atlas Vector Search not available: {e}")
            logger.info("Falling back to cosine similarity search")
            self._use_atlas_search = False

        return self._use_atlas_search

    async def retrieve(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks using vector similarity.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters (folder_paths, access_tags, etc.)

        Returns:
            List of retrieved chunks sorted by similarity score
        """
        k = top_k if top_k is not None else self.config.top_k
        filters = filters or {}

        # Generate query embedding
        embedder = await self._get_embedder()
        query_embedding = await embedder.embed_query(query)

        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []

        # Check if Atlas Vector Search is available
        use_atlas = await self._check_atlas_search()

        if use_atlas:
            chunks = await self._search_with_atlas(
                query_embedding=query_embedding,
                config_id=config_id,
                top_k=k,
                filters=filters,
            )
        else:
            chunks = await self._search_with_cosine(
                query_embedding=query_embedding,
                config_id=config_id,
                top_k=k,
                filters=filters,
            )

        # Apply score threshold
        chunks = self._apply_score_threshold(chunks)

        return chunks

    async def _search_with_atlas(
        self,
        query_embedding: List[float],
        config_id: str,
        top_k: int,
        filters: Dict[str, Any],
    ) -> List[RetrievedChunk]:
        """Search using MongoDB Atlas Vector Search."""
        # Build filter for vector search
        vector_filter: Dict[str, Any] = {"config_id": config_id}

        # Add folder path filter (for RBAC)
        if "folder_paths" in filters and filters["folder_paths"]:
            vector_filter["folder_path"] = {"$in": filters["folder_paths"]}
        elif self.config.folder_paths:
            vector_filter["folder_path"] = {"$in": self.config.folder_paths}

        # Add access tags filter
        if "access_tags" in filters and filters["access_tags"]:
            vector_filter["access_tags"] = {"$in": filters["access_tags"]}

        # Add file type filter
        if "file_types" in filters and filters["file_types"]:
            vector_filter["file_type"] = {"$in": filters["file_types"]}

        # Build aggregation pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.config.vector_index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": self.config.num_candidates,
                    "limit": top_k,
                    "filter": vector_filter,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "document_id": 1,
                    "config_id": 1,
                    "chunk_index": 1,
                    "start_char": 1,
                    "end_char": 1,
                    "folder_path": 1,
                    "access_tags": 1,
                    "metadata": 1,
                    "created_at": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        # Execute search
        cursor = self.chunks.aggregate(pipeline)
        results = await cursor.to_list(length=top_k)

        # Convert to RetrievedChunk objects
        chunks = []
        for doc in results:
            score = doc.get("score", 0.0)

            # Enrich with document metadata
            doc_metadata = await self._get_document_metadata(doc.get("document_id"))
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=score,
                source_type=SourceType.VECTOR,
            )
            chunks.append(chunk)

        return chunks

    async def _search_with_cosine(
        self,
        query_embedding: List[float],
        config_id: str,
        top_k: int,
        filters: Dict[str, Any],
    ) -> List[RetrievedChunk]:
        """Search using in-memory cosine similarity (fallback)."""
        # Build query filter
        query_filter: Dict[str, Any] = {
            "config_id": config_id,
            "embedding": {"$exists": True, "$ne": []},
        }

        # Add folder path filter
        if "folder_paths" in filters and filters["folder_paths"]:
            query_filter["folder_path"] = {"$in": filters["folder_paths"]}
        elif self.config.folder_paths:
            query_filter["folder_path"] = {"$in": self.config.folder_paths}

        # Add access tags filter
        if "access_tags" in filters and filters["access_tags"]:
            query_filter["access_tags"] = {"$in": filters["access_tags"]}

        # Add file type filter
        if "file_types" in filters and filters["file_types"]:
            query_filter["file_type"] = {"$in": filters["file_types"]}

        # Fetch chunks with embeddings
        cursor = self.chunks.find(query_filter)
        docs = await cursor.to_list(length=1000)  # Limit for performance

        if not docs:
            return []

        # Calculate cosine similarity for each chunk
        scored_chunks = []
        for doc in docs:
            chunk_embedding = doc.get("embedding", [])
            if not chunk_embedding:
                continue

            score = self._cosine_similarity(query_embedding, chunk_embedding)

            # Enrich with document metadata
            doc_metadata = await self._get_document_metadata(doc.get("document_id"))
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=score,
                source_type=SourceType.VECTOR,
            )
            scored_chunks.append(chunk)

        # Sort by score descending and take top_k
        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks[:top_k]

    def _cosine_similarity(
        self, vec1: List[float], vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _get_document_metadata(
        self, document_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get document metadata for enrichment."""
        if not document_id:
            return None

        try:
            doc = await self.db["documents"].find_one(
                {"_id": document_id},
                {"file_name": 1, "file_path": 1, "file_type": 1},
            )
            return doc
        except Exception:
            return None

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[RetrievedChunk]:
        """Get a specific chunk by ID."""
        doc = await self.chunks.find_one({"_id": chunk_id})
        if not doc:
            return None

        # Enrich with document metadata
        doc_metadata = await self._get_document_metadata(doc.get("document_id"))
        if doc_metadata:
            doc["file_name"] = doc_metadata.get("file_name")
            doc["file_path"] = doc_metadata.get("file_path")
            doc["file_type"] = doc_metadata.get("file_type")

        return RetrievedChunk.from_mongo_doc(
            doc=doc,
            score=1.0,  # Direct fetch, full score
            source_type=SourceType.VECTOR,
        )

    async def get_chunks_by_document(
        self, document_id: str, include_embeddings: bool = False
    ) -> List[RetrievedChunk]:
        """Get all chunks for a document."""
        projection = None if include_embeddings else {"embedding": 0}

        cursor = self.chunks.find(
            {"document_id": document_id},
            projection,
        ).sort("chunk_index", 1)

        docs = await cursor.to_list(length=None)

        # Enrich with document metadata
        doc_metadata = await self._get_document_metadata(document_id)

        chunks = []
        for doc in docs:
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=1.0,
                source_type=SourceType.VECTOR,
            )
            chunks.append(chunk)

        return chunks
