"""Hybrid retriever combining multiple retrieval methods."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievalResult,
    RetrievedChunk,
    SourceType,
)

logger = logging.getLogger(__name__)


class FusionMethod(str, Enum):
    """Score fusion methods."""

    RRF = "rrf"  # Reciprocal Rank Fusion
    LINEAR = "linear"  # Weighted linear combination
    MAX = "max"  # Maximum score
    SUM = "sum"  # Sum of scores


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval."""

    # Enabled retrievers
    use_vector: bool = True
    use_keyword: bool = True
    use_graph: bool = False

    # Fusion settings
    fusion_method: FusionMethod = FusionMethod.RRF
    rrf_k: int = 60  # RRF constant

    # Retriever weights (for linear fusion)
    vector_weight: float = 0.5
    keyword_weight: float = 0.3
    graph_weight: float = 0.2

    # Result settings
    top_k: int = 10
    min_score: float = 0.0
    deduplicate: bool = True

    # Per-retriever limits (fetch more, then fuse and trim)
    vector_top_k: int = 20
    keyword_top_k: int = 20
    graph_top_k: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridConfig":
        """Create from dictionary."""
        fusion_method = data.get("fusion_method", "rrf")
        if isinstance(fusion_method, str):
            fusion_method = FusionMethod(fusion_method)

        return cls(
            use_vector=data.get("use_vector", True),
            use_keyword=data.get("use_keyword", True),
            use_graph=data.get("use_graph", False),
            fusion_method=fusion_method,
            rrf_k=data.get("rrf_k", 60),
            vector_weight=data.get("vector_weight", 0.5),
            keyword_weight=data.get("keyword_weight", 0.3),
            graph_weight=data.get("graph_weight", 0.2),
            top_k=data.get("top_k", 10),
            min_score=data.get("min_score", 0.0),
            deduplicate=data.get("deduplicate", True),
            vector_top_k=data.get("vector_top_k", 20),
            keyword_top_k=data.get("keyword_top_k", 20),
            graph_top_k=data.get("graph_top_k", 10),
        )


@dataclass
class HybridRetrievalResult:
    """Result of hybrid retrieval."""

    chunks: List[RetrievedChunk]
    source_results: Dict[str, List[RetrievedChunk]] = field(default_factory=dict)
    fusion_scores: Dict[str, float] = field(default_factory=dict)
    retrieval_time_ms: float = 0.0
    source_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "source_counts": self.source_counts,
            "retrieval_time_ms": self.retrieval_time_ms,
            "total_results": len(self.chunks),
        }


class HybridRetriever(BaseRetriever):
    """
    Combines multiple retrieval methods with score fusion.

    Supported retrievers:
    - Vector (semantic similarity)
    - Keyword (full-text search)
    - Graph (knowledge graph traversal)

    Fusion methods:
    - RRF: Reciprocal Rank Fusion
    - Linear: Weighted linear combination
    - Max: Maximum score across retrievers
    - Sum: Sum of scores
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        config: Optional[RetrievalConfig] = None,
        hybrid_config: Optional[HybridConfig] = None,
    ):
        """
        Initialize hybrid retriever.

        Args:
            db: MongoDB database instance
            config: Base retrieval configuration
            hybrid_config: Hybrid-specific configuration
        """
        super().__init__(config)
        self.db = db
        self.hybrid_config = hybrid_config or HybridConfig()

        # Lazy-initialized retrievers
        self._vector_retriever = None
        self._keyword_retriever = None
        self._graph_retriever = None

    async def _get_vector_retriever(self):
        """Get or create vector retriever."""
        if self._vector_retriever is None:
            from app.retrieval.vector import VectorRetriever

            self._vector_retriever = VectorRetriever(
                db=self.db,
                config=self.config,
            )
        return self._vector_retriever

    async def _get_keyword_retriever(self):
        """Get or create keyword retriever."""
        if self._keyword_retriever is None:
            from app.retrieval.keyword import KeywordRetriever

            self._keyword_retriever = KeywordRetriever(
                db=self.db,
                config=self.config,
            )
        return self._keyword_retriever

    async def _get_graph_retriever(self):
        """Get or create graph retriever."""
        if self._graph_retriever is None:
            from app.retrieval.graph import GraphRetriever

            self._graph_retriever = GraphRetriever(
                db=self.db,
                config=self.config,
            )
        return self._graph_retriever

    async def close(self) -> None:
        """Clean up resources."""
        if self._vector_retriever and hasattr(self._vector_retriever, "close"):
            await self._vector_retriever.close()
        if self._keyword_retriever and hasattr(self._keyword_retriever, "close"):
            await self._keyword_retriever.close()
        if self._graph_retriever and hasattr(self._graph_retriever, "close"):
            await self._graph_retriever.close()

    async def retrieve(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks using multiple methods.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters

        Returns:
            List of retrieved chunks with fused scores
        """
        result = await self.retrieve_with_details(
            query=query,
            config_id=config_id,
            top_k=top_k,
            filters=filters,
        )
        return result.chunks

    async def retrieve_with_details(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> HybridRetrievalResult:
        """
        Retrieve with full details about source contributions.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters

        Returns:
            HybridRetrievalResult with detailed information
        """
        import asyncio
        import time

        start_time = time.time()
        k = top_k if top_k is not None else self.hybrid_config.top_k
        filters = filters or {}

        # Collect results from enabled retrievers in parallel
        tasks = []
        retriever_names = []

        if self.hybrid_config.use_vector:
            retriever = await self._get_vector_retriever()
            tasks.append(
                retriever.retrieve(
                    query=query,
                    config_id=config_id,
                    top_k=self.hybrid_config.vector_top_k,
                    filters=filters,
                )
            )
            retriever_names.append("vector")

        if self.hybrid_config.use_keyword:
            retriever = await self._get_keyword_retriever()
            tasks.append(
                retriever.retrieve(
                    query=query,
                    config_id=config_id,
                    top_k=self.hybrid_config.keyword_top_k,
                    filters=filters,
                )
            )
            retriever_names.append("keyword")

        if self.hybrid_config.use_graph:
            retriever = await self._get_graph_retriever()
            tasks.append(
                retriever.retrieve(
                    query=query,
                    config_id=config_id,
                    top_k=self.hybrid_config.graph_top_k,
                    filters=filters,
                )
            )
            retriever_names.append("graph")

        # Execute retrievers in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results by source
        source_results: Dict[str, List[RetrievedChunk]] = {}
        source_counts: Dict[str, int] = {}

        for name, result in zip(retriever_names, results):
            if isinstance(result, Exception):
                logger.error(f"{name} retriever failed: {result}")
                source_results[name] = []
                source_counts[name] = 0
            else:
                source_results[name] = result
                source_counts[name] = len(result)

        # Fuse results
        fused_chunks, fusion_scores = self._fuse_results(source_results)

        # Apply score threshold
        if self.hybrid_config.min_score > 0:
            fused_chunks = [
                c for c in fused_chunks
                if fusion_scores.get(c.chunk_id, 0) >= self.hybrid_config.min_score
            ]

        # Take top_k
        fused_chunks = fused_chunks[:k]

        retrieval_time = (time.time() - start_time) * 1000

        return HybridRetrievalResult(
            chunks=fused_chunks,
            source_results=source_results,
            fusion_scores=fusion_scores,
            retrieval_time_ms=retrieval_time,
            source_counts=source_counts,
        )

    def _fuse_results(
        self,
        source_results: Dict[str, List[RetrievedChunk]],
    ) -> tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Fuse results from multiple retrievers.

        Args:
            source_results: Results from each retriever

        Returns:
            Tuple of (fused chunks, fusion scores)
        """
        if self.hybrid_config.fusion_method == FusionMethod.RRF:
            return self._rrf_fusion(source_results)
        elif self.hybrid_config.fusion_method == FusionMethod.LINEAR:
            return self._linear_fusion(source_results)
        elif self.hybrid_config.fusion_method == FusionMethod.MAX:
            return self._max_fusion(source_results)
        elif self.hybrid_config.fusion_method == FusionMethod.SUM:
            return self._sum_fusion(source_results)
        else:
            return self._rrf_fusion(source_results)

    def _rrf_fusion(
        self,
        source_results: Dict[str, List[RetrievedChunk]],
    ) -> tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Apply Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (k + rank + 1)) for each ranking
        """
        k = self.hybrid_config.rrf_k
        scores: Dict[str, float] = defaultdict(float)
        chunks_by_id: Dict[str, RetrievedChunk] = {}

        for source, chunks in source_results.items():
            for rank, chunk in enumerate(chunks):
                chunk_id = chunk.chunk_id
                scores[chunk_id] += 1.0 / (k + rank + 1)

                # Keep the chunk with highest original score
                if chunk_id not in chunks_by_id or chunk.score > chunks_by_id[chunk_id].score:
                    chunks_by_id[chunk_id] = chunk

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result list
        fused_chunks = []
        for chunk_id in sorted_ids:
            chunk = chunks_by_id[chunk_id]
            # Update score with fused score
            chunk.score = scores[chunk_id]
            chunk.source_type = SourceType.HYBRID
            fused_chunks.append(chunk)

        return fused_chunks, dict(scores)

    def _linear_fusion(
        self,
        source_results: Dict[str, List[RetrievedChunk]],
    ) -> tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Apply weighted linear combination.

        score = sum(weight_i * normalized_score_i)
        """
        weights = {
            "vector": self.hybrid_config.vector_weight,
            "keyword": self.hybrid_config.keyword_weight,
            "graph": self.hybrid_config.graph_weight,
        }

        scores: Dict[str, float] = defaultdict(float)
        chunks_by_id: Dict[str, RetrievedChunk] = {}

        for source, chunks in source_results.items():
            weight = weights.get(source, 0.0)
            if not chunks or weight == 0:
                continue

            # Normalize scores within source (0-1 range)
            max_score = max(c.score for c in chunks) if chunks else 1.0
            if max_score == 0:
                max_score = 1.0

            for chunk in chunks:
                chunk_id = chunk.chunk_id
                normalized_score = chunk.score / max_score
                scores[chunk_id] += weight * normalized_score

                if chunk_id not in chunks_by_id or chunk.score > chunks_by_id[chunk_id].score:
                    chunks_by_id[chunk_id] = chunk

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_chunks = []
        for chunk_id in sorted_ids:
            chunk = chunks_by_id[chunk_id]
            chunk.score = scores[chunk_id]
            chunk.source_type = SourceType.HYBRID
            fused_chunks.append(chunk)

        return fused_chunks, dict(scores)

    def _max_fusion(
        self,
        source_results: Dict[str, List[RetrievedChunk]],
    ) -> tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Use maximum score across all retrievers.
        """
        scores: Dict[str, float] = {}
        chunks_by_id: Dict[str, RetrievedChunk] = {}

        for source, chunks in source_results.items():
            for chunk in chunks:
                chunk_id = chunk.chunk_id
                current_score = scores.get(chunk_id, 0.0)

                if chunk.score > current_score:
                    scores[chunk_id] = chunk.score
                    chunks_by_id[chunk_id] = chunk

        # Sort by score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_chunks = []
        for chunk_id in sorted_ids:
            chunk = chunks_by_id[chunk_id]
            chunk.source_type = SourceType.HYBRID
            fused_chunks.append(chunk)

        return fused_chunks, scores

    def _sum_fusion(
        self,
        source_results: Dict[str, List[RetrievedChunk]],
    ) -> tuple[List[RetrievedChunk], Dict[str, float]]:
        """
        Sum scores across all retrievers.
        """
        scores: Dict[str, float] = defaultdict(float)
        chunks_by_id: Dict[str, RetrievedChunk] = {}

        for source, chunks in source_results.items():
            for chunk in chunks:
                chunk_id = chunk.chunk_id
                scores[chunk_id] += chunk.score

                if chunk_id not in chunks_by_id or chunk.score > chunks_by_id[chunk_id].score:
                    chunks_by_id[chunk_id] = chunk

        # Sort by score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_chunks = []
        for chunk_id in sorted_ids:
            chunk = chunks_by_id[chunk_id]
            chunk.score = scores[chunk_id]
            chunk.source_type = SourceType.HYBRID
            fused_chunks.append(chunk)

        return fused_chunks, dict(scores)


def reciprocal_rank_fusion(
    rankings: List[List[str]],
    k: int = 60,
) -> Dict[str, float]:
    """
    Standalone RRF function for external use.

    Args:
        rankings: List of ranked document ID lists
        k: RRF constant (typically 60)

    Returns:
        Dictionary mapping doc_id to fused score
    """
    scores: Dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] += 1.0 / (k + rank + 1)
    return dict(scores)
