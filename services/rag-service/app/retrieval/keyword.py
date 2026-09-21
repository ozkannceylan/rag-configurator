"""Keyword retriever using MongoDB Atlas Search or text index fallback."""

import logging
import re
from dataclasses import dataclass
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievedChunk,
    SourceType,
)

logger = logging.getLogger(__name__)


@dataclass
class KeywordConfig:
    """Configuration for keyword search."""

    # Basic settings
    top_k: int = 10
    min_score: float = 0.0

    # Fuzzy matching
    use_fuzzy: bool = True
    max_edits: int = 1  # Levenshtein distance for fuzzy matching

    # Atlas Search settings
    search_index_name: str = "search_index"

    # Boost factor for hybrid scoring
    boost_factor: float = 1.0

    # Field weights
    content_weight: float = 1.0
    metadata_weight: float = 0.5

    # Filter settings
    folder_paths: list[str] | None = None
    access_tags: list[str] | None = None
    file_types: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeywordConfig":
        """Create from dictionary."""
        return cls(
            top_k=data.get("top_k", 10),
            min_score=data.get("min_score", 0.0),
            use_fuzzy=data.get("use_fuzzy", True),
            max_edits=data.get("max_edits", 1),
            search_index_name=data.get("search_index_name", "search_index"),
            boost_factor=data.get("boost_factor", 1.0),
            content_weight=data.get("content_weight", 1.0),
            metadata_weight=data.get("metadata_weight", 0.5),
            folder_paths=data.get("folder_paths"),
            access_tags=data.get("access_tags"),
            file_types=data.get("file_types"),
        )


class KeywordRetriever(BaseRetriever):
    """
    Keyword/full-text search retriever for MongoDB.

    Supports two modes:
    1. MongoDB Atlas Search ($search) - for production
    2. MongoDB text index ($text) - fallback for development

    Automatically falls back to text index if Atlas Search is unavailable.
    """

    CHUNKS_COLLECTION = "chunks"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: RetrievalConfig | None = None,
        keyword_config: KeywordConfig | None = None,
    ):
        """
        Initialize keyword retriever.

        Args:
            db: MongoDB database instance
            config: Base retrieval configuration
            keyword_config: Keyword-specific configuration
        """
        super().__init__(config)
        self.db = db
        self.chunks = db[self.CHUNKS_COLLECTION]
        self.keyword_config = keyword_config or KeywordConfig()
        self._use_atlas_search: bool | None = None

    async def _check_atlas_search(self) -> bool:
        """Check if MongoDB Atlas Search is available."""
        if self._use_atlas_search is not None:
            return self._use_atlas_search

        try:
            # Try a simple search to check if index exists
            pipeline = [
                {
                    "$search": {
                        "index": self.keyword_config.search_index_name,
                        "text": {
                            "query": "test",
                            "path": "content",
                        },
                    }
                },
                {"$limit": 1},
            ]
            await self.chunks.aggregate(pipeline).to_list(length=1)
            self._use_atlas_search = True
            logger.info("MongoDB Atlas Search is available")
        except Exception as e:
            logger.info(f"MongoDB Atlas Search not available: {e}")
            logger.info("Falling back to text index search")
            self._use_atlas_search = False

        return self._use_atlas_search

    async def _ensure_text_index(self) -> None:
        """Ensure text index exists for fallback search."""
        try:
            await self.chunks.create_index(
                [("content", "text")],
                name="content_text_index",
                default_language="english",
            )
        except Exception as e:
            logger.debug(f"Text index may already exist: {e}")

    async def retrieve(
        self,
        query: str,
        config_id: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks using keyword search.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters (folder_paths, access_tags, etc.)

        Returns:
            List of retrieved chunks sorted by relevance
        """
        if not query or not query.strip():
            return []

        k = top_k if top_k is not None else self.keyword_config.top_k
        filters = filters or {}

        # Check if Atlas Search is available
        use_atlas = await self._check_atlas_search()

        if use_atlas:
            chunks = await self._search_with_atlas(
                query=query,
                config_id=config_id,
                top_k=k,
                filters=filters,
            )
        else:
            chunks = await self._search_with_text_index(
                query=query,
                config_id=config_id,
                top_k=k,
                filters=filters,
            )

        # Apply score threshold
        chunks = self._apply_score_threshold(chunks, self.keyword_config.min_score)

        # Apply boost factor
        if self.keyword_config.boost_factor != 1.0:
            for chunk in chunks:
                chunk.score *= self.keyword_config.boost_factor

        return chunks

    async def _search_with_atlas(
        self,
        query: str,
        config_id: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[RetrievedChunk]:
        """Search using MongoDB Atlas Search."""
        # Build text search clause
        text_clause: dict[str, Any] = {
            "text": {
                "query": query,
                "path": "content",
            }
        }

        # Add fuzzy matching if enabled
        if self.keyword_config.use_fuzzy:
            text_clause["text"]["fuzzy"] = {
                "maxEdits": self.keyword_config.max_edits,
            }

        # Build filter clauses
        filter_clauses: list[dict[str, Any]] = [
            {"equals": {"path": "config_id", "value": config_id}}
        ]

        # Add folder path filter (for RBAC)
        folder_paths = filters.get("folder_paths") or self.keyword_config.folder_paths
        if folder_paths:
            filter_clauses.append(
                {"in": {"path": "folder_path", "value": folder_paths}}
            )

        # Add access tags filter
        access_tags = filters.get("access_tags") or self.keyword_config.access_tags
        if access_tags:
            filter_clauses.append({"in": {"path": "access_tags", "value": access_tags}})

        # Add file type filter
        file_types = filters.get("file_types") or self.keyword_config.file_types
        if file_types:
            filter_clauses.append({"in": {"path": "file_type", "value": file_types}})

        # Build aggregation pipeline
        pipeline = [
            {
                "$search": {
                    "index": self.keyword_config.search_index_name,
                    "compound": {
                        "must": [text_clause],
                        "filter": filter_clauses,
                    },
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
                    "score": {"$meta": "searchScore"},
                }
            },
            {"$limit": top_k},
        ]

        # Execute search
        cursor = self.chunks.aggregate(pipeline)
        results = await cursor.to_list(length=top_k)

        # Convert to RetrievedChunk objects
        chunks = []
        for doc in results:
            score = doc.get("score", 0.0)

            # Normalize score (Atlas Search scores can be > 1)
            normalized_score = min(score / 10.0, 1.0) if score > 1 else score

            # Enrich with document metadata
            doc_metadata = await self._get_document_metadata(doc.get("document_id"))
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=normalized_score,
                source_type=SourceType.KEYWORD,
            )
            chunks.append(chunk)

        return chunks

    async def _search_with_text_index(
        self,
        query: str,
        config_id: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[RetrievedChunk]:
        """Search using MongoDB text index (fallback)."""
        # Ensure text index exists
        await self._ensure_text_index()

        # Build query filter
        query_filter: dict[str, Any] = {
            "config_id": config_id,
            "$text": {"$search": query},
        }

        # Add folder path filter
        folder_paths = filters.get("folder_paths") or self.keyword_config.folder_paths
        if folder_paths:
            query_filter["folder_path"] = {"$in": folder_paths}

        # Add access tags filter
        access_tags = filters.get("access_tags") or self.keyword_config.access_tags
        if access_tags:
            query_filter["access_tags"] = {"$in": access_tags}

        # Add file type filter
        file_types = filters.get("file_types") or self.keyword_config.file_types
        if file_types:
            query_filter["file_type"] = {"$in": file_types}

        # Execute search with text score
        cursor = (
            self.chunks.find(
                query_filter,
                {"score": {"$meta": "textScore"}},
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(top_k)
        )

        results = await cursor.to_list(length=top_k)

        # Convert to RetrievedChunk objects
        chunks = []
        max_score = max((doc.get("score", 0) for doc in results), default=1.0)

        for doc in results:
            score = doc.get("score", 0.0)

            # Normalize score to 0-1 range
            normalized_score = score / max_score if max_score > 0 else 0.0

            # Enrich with document metadata
            doc_metadata = await self._get_document_metadata(doc.get("document_id"))
            if doc_metadata:
                doc["file_name"] = doc_metadata.get("file_name")
                doc["file_path"] = doc_metadata.get("file_path")
                doc["file_type"] = doc_metadata.get("file_type")

            chunk = RetrievedChunk.from_mongo_doc(
                doc=doc,
                score=normalized_score,
                source_type=SourceType.KEYWORD,
            )
            chunks.append(chunk)

        return chunks

    async def _get_document_metadata(
        self, document_id: str | None
    ) -> dict[str, Any] | None:
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

    async def search_with_highlights(
        self,
        query: str,
        config_id: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search with highlighted snippets (Atlas Search only).

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters

        Returns:
            List of results with highlights
        """
        use_atlas = await self._check_atlas_search()
        if not use_atlas:
            # Fall back to regular search for non-Atlas
            chunks = await self.retrieve(query, config_id, top_k, filters)
            return [
                {
                    "chunk": chunk.to_dict(),
                    "highlights": self._generate_simple_highlights(
                        chunk.content, query
                    ),
                }
                for chunk in chunks
            ]

        k = top_k if top_k is not None else self.keyword_config.top_k
        filters = filters or {}

        # Build search with highlights
        pipeline = [
            {
                "$search": {
                    "index": self.keyword_config.search_index_name,
                    "compound": {
                        "must": [
                            {
                                "text": {
                                    "query": query,
                                    "path": "content",
                                }
                            }
                        ],
                        "filter": [
                            {"equals": {"path": "config_id", "value": config_id}}
                        ],
                    },
                    "highlight": {
                        "path": "content",
                        "maxNumPassages": 3,
                    },
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "document_id": 1,
                    "config_id": 1,
                    "chunk_index": 1,
                    "folder_path": 1,
                    "score": {"$meta": "searchScore"},
                    "highlights": {"$meta": "searchHighlights"},
                }
            },
            {"$limit": k},
        ]

        cursor = self.chunks.aggregate(pipeline)
        results = await cursor.to_list(length=k)

        # Format results with highlights
        formatted = []
        for doc in results:
            highlights = doc.get("highlights", [])
            highlight_texts = []
            for h in highlights:
                texts = h.get("texts", [])
                for t in texts:
                    if t.get("type") == "hit":
                        highlight_texts.append(t.get("value", ""))

            formatted.append(
                {
                    "chunk_id": str(doc.get("_id")),
                    "content": doc.get("content", ""),
                    "score": doc.get("score", 0.0),
                    "highlights": highlight_texts,
                }
            )

        return formatted

    def _generate_simple_highlights(
        self, content: str, query: str, context_chars: int = 50
    ) -> list[str]:
        """Generate simple highlights without Atlas Search."""
        highlights = []
        query_terms = query.lower().split()
        content_lower = content.lower()

        for term in query_terms:
            start = 0
            while True:
                idx = content_lower.find(term, start)
                if idx == -1:
                    break

                # Extract context around the match
                ctx_start = max(0, idx - context_chars)
                ctx_end = min(len(content), idx + len(term) + context_chars)

                snippet = content[ctx_start:ctx_end]
                if ctx_start > 0:
                    snippet = "..." + snippet
                if ctx_end < len(content):
                    snippet = snippet + "..."

                highlights.append(snippet)
                start = idx + 1

                if len(highlights) >= 3:
                    break

            if len(highlights) >= 3:
                break

        return highlights

    async def get_suggestions(
        self,
        prefix: str,
        config_id: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get autocomplete suggestions for a query prefix.

        Args:
            prefix: Query prefix
            config_id: Configuration ID
            limit: Maximum suggestions to return

        Returns:
            List of suggested completions
        """
        use_atlas = await self._check_atlas_search()

        if use_atlas:
            # Use Atlas Search autocomplete
            pipeline = [
                {
                    "$search": {
                        "index": self.keyword_config.search_index_name,
                        "autocomplete": {
                            "query": prefix,
                            "path": "content",
                            "tokenOrder": "sequential",
                        },
                    }
                },
                {"$match": {"config_id": config_id}},
                {"$limit": limit},
                {"$project": {"content": 1}},
            ]

            try:
                cursor = self.chunks.aggregate(pipeline)
                results = await cursor.to_list(length=limit)

                # Extract relevant phrases
                suggestions = []
                for doc in results:
                    content = doc.get("content", "")
                    # Find the matching phrase
                    words = content.split()
                    for i, word in enumerate(words):
                        if word.lower().startswith(prefix.lower()):
                            # Get a few words for context
                            phrase = " ".join(words[i : i + 3])
                            if phrase not in suggestions:
                                suggestions.append(phrase)
                            break
                    if len(suggestions) >= limit:
                        break

                return suggestions[:limit]
            except Exception as e:
                logger.debug(f"Autocomplete failed: {e}")

        # Fallback: simple prefix matching
        cursor = self.chunks.find(
            {
                "config_id": config_id,
                "content": {"$regex": f"\\b{re.escape(prefix)}", "$options": "i"},
            },
            {"content": 1},
        ).limit(limit * 2)

        results = await cursor.to_list(length=limit * 2)
        suggestions = []

        for doc in results:
            content = doc.get("content", "")
            # Find matching words
            pattern = re.compile(rf"\b{re.escape(prefix)}\w*", re.IGNORECASE)
            matches = pattern.findall(content)
            for match in matches:
                if match not in suggestions:
                    suggestions.append(match)
                if len(suggestions) >= limit:
                    break
            if len(suggestions) >= limit:
                break

        return suggestions[:limit]
