"""Retrieval module for RAG pipelines."""

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievedChunk,
    SourceType,
)
from app.retrieval.factory import (
    RetrievalMethod,
    get_retriever,
    get_retriever_from_config,
)
from app.retrieval.graph import (
    GraphConfig,
    GraphContext,
    GraphEdge,
    GraphNode,
    GraphRetriever,
)
from app.retrieval.hybrid import (
    FusionMethod,
    HybridConfig,
    HybridRetriever,
    reciprocal_rank_fusion,
)
from app.retrieval.keyword import KeywordConfig, KeywordRetriever
from app.retrieval.vector import VectorRetriever

__all__ = [
    # Base
    "BaseRetriever",
    "RetrievedChunk",
    "RetrievalConfig",
    "SourceType",
    # Vector
    "VectorRetriever",
    # Keyword
    "KeywordRetriever",
    "KeywordConfig",
    # Graph
    "GraphRetriever",
    "GraphConfig",
    "GraphContext",
    "GraphNode",
    "GraphEdge",
    # Hybrid
    "HybridRetriever",
    "HybridConfig",
    "FusionMethod",
    "reciprocal_rank_fusion",
    # Factory
    "get_retriever",
    "get_retriever_from_config",
    "RetrievalMethod",
]
